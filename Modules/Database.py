from email.mime import image
import os, sqlite3, re, json, time
from typing import Optional, Any

DATABASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Media", "Database.db"))

def _ensure_column(cur: sqlite3.Cursor, table: str, col_def_sql: str) -> None:
    """
    Adds a column if missing. col_def_sql example: "pokemon_skipped INTEGER NOT NULL DEFAULT 0"
    """
    col_name = col_def_sql.split()[0]
    cur.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cur.fetchall()}  # row[1] is name
    if col_name not in existing:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_def_sql}")

def initialize_database(db_file: str = DATABASE_PATH) -> None:
    os.makedirs(os.path.dirname(db_file), exist_ok=True)

    with sqlite3.connect(db_file, timeout=5) as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute("PRAGMA synchronous=NORMAL;")
        cur.execute("PRAGMA foreign_keys=ON;")

        # Main totals table (all programs)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS program_stats (
                game TEXT NOT NULL,
                program TEXT NOT NULL,

                runs INTEGER NOT NULL DEFAULT 0,
                resets INTEGER NOT NULL DEFAULT 0,
                encounters INTEGER NOT NULL DEFAULT 0,

                actions INTEGER NOT NULL DEFAULT 0,
                action_hits INTEGER NOT NULL DEFAULT 0,

                eggs_collected INTEGER NOT NULL DEFAULT 0,
                eggs_hatched INTEGER NOT NULL DEFAULT 0,

                pokemon_encountered INTEGER NOT NULL DEFAULT 0,
                pokemon_caught INTEGER NOT NULL DEFAULT 0,
                pokemon_released INTEGER NOT NULL DEFAULT 0,
                pokemon_skipped INTEGER NOT NULL DEFAULT 0,

                shinies INTEGER NOT NULL DEFAULT 0,
                playtime_seconds INTEGER NOT NULL DEFAULT 0,

                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),

                PRIMARY KEY (game, program)
            )
        """)

        # Ensure older DBs get missing columns (safe no-ops if already present)
        _ensure_column(cur, "program_stats", "encounters INTEGER NOT NULL DEFAULT 0")
        _ensure_column(cur, "program_stats", "pokemon_skipped INTEGER NOT NULL DEFAULT 0")

        # Per-pokemon totals
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pokemon_stats (
                game TEXT NOT NULL,
                program TEXT NOT NULL,
                pokemon_name TEXT NOT NULL,

                encountered INTEGER NOT NULL DEFAULT 0,
                caught INTEGER NOT NULL DEFAULT 0,
                shinies INTEGER NOT NULL DEFAULT 0,
                eggs_hatched INTEGER NOT NULL DEFAULT 0,

                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),

                PRIMARY KEY (game, program, pokemon_name),

                FOREIGN KEY (game, program)
                REFERENCES program_stats(game, program)
                ON DELETE CASCADE
            )
        """)

        _ensure_column(cur, "pokemon_stats", "eggs_hatched INTEGER NOT NULL DEFAULT 0")

        cur.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_stats_game_program ON pokemon_stats(game, program)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_program_stats_game ON program_stats(game)")

        # IMPORTANT: remove the rollup triggers to prevent double counting
        cur.execute("DROP TRIGGER IF EXISTS trg_pokemon_stats_ai;")
        cur.execute("DROP TRIGGER IF EXISTS trg_pokemon_stats_au;")

        conn.commit()

def ensure_program_row(game: str, program: str, db_file: str = DATABASE_PATH) -> None:
    with sqlite3.connect(db_file, timeout=5) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO program_stats (game, program)
            VALUES (?, ?)
        """, (game, program))
        conn.commit()

def add_program_deltas(
    game: str,
    program: str,
    *,
    runs_delta: int = 0,
    resets_delta: int = 0,
    encounters_delta: int = 0,
    actions_delta: int = 0,
    action_hits_delta: int = 0,
    eggs_collected_delta: int = 0,
    eggs_hatched_delta: int = 0,
    pokemon_encountered_delta: int = 0,
    pokemon_caught_delta: int = 0,
    pokemon_released_delta: int = 0,
    pokemon_skipped_delta: int = 0,
    shinies_delta: int = 0,
    playtime_seconds_delta: int = 0,
    db_file: str = DATABASE_PATH,
) -> None:
    if not game or not program:
        raise ValueError("game and program are required")

    deltas = (
        runs_delta, resets_delta, encounters_delta,
        actions_delta, action_hits_delta,
        eggs_collected_delta, eggs_hatched_delta,
        pokemon_encountered_delta, pokemon_caught_delta,
        pokemon_released_delta, pokemon_skipped_delta,
        shinies_delta, playtime_seconds_delta,
    )
    if any(d < 0 for d in deltas):
        raise ValueError("deltas must be >= 0")
    if all(d == 0 for d in deltas):
        return

    ensure_program_row(game, program, db_file=db_file)

    with sqlite3.connect(db_file, timeout=5) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE program_stats
            SET
                runs = runs + ?,
                resets = resets + ?,
                encounters = encounters + ?,
                actions = actions + ?,
                action_hits = action_hits + ?,
                eggs_collected = eggs_collected + ?,
                eggs_hatched = eggs_hatched + ?,
                pokemon_encountered = pokemon_encountered + ?,
                pokemon_caught = pokemon_caught + ?,
                pokemon_released = pokemon_released + ?,
                pokemon_skipped = pokemon_skipped + ?,
                shinies = shinies + ?,
                playtime_seconds = playtime_seconds + ?,
                updated_at = datetime('now')
            WHERE game = ? AND program = ?
            """,
            (
                int(runs_delta),
                int(resets_delta),
                int(encounters_delta),
                int(actions_delta),
                int(action_hits_delta),
                int(eggs_collected_delta),
                int(eggs_hatched_delta),
                int(pokemon_encountered_delta),
                int(pokemon_caught_delta),
                int(pokemon_released_delta),
                int(pokemon_skipped_delta),
                int(shinies_delta),
                int(playtime_seconds_delta),
                game,
                program,
            ),
        )
        conn.commit()

def add_pokemon_delta(
    game: str,
    program: str,
    pokemon_name: str,
    *,
    encountered_delta: int = 0,
    caught_delta: int = 0,
    shinies_delta: int = 0,
    eggs_hatched_delta: int = 0,
    db_file: str = DATABASE_PATH,
) -> None:
    if not game or not program or not pokemon_name:
        raise ValueError("game, program, pokemon_name are required")
    if any(d < 0 for d in (encountered_delta, caught_delta, shinies_delta, eggs_hatched_delta)):
        raise ValueError("deltas must be >= 0")
    if all(d == 0 for d in (encountered_delta, caught_delta, shinies_delta, eggs_hatched_delta)):
        return

    ensure_program_row(game, program, db_file=db_file)

    with sqlite3.connect(db_file, timeout=5) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO pokemon_stats (
                game, program, pokemon_name,
                encountered, caught, shinies, eggs_hatched
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(game, program, pokemon_name) DO UPDATE SET
                encountered   = encountered   + excluded.encountered,
                caught        = caught        + excluded.caught,
                shinies       = shinies       + excluded.shinies,
                eggs_hatched  = eggs_hatched  + excluded.eggs_hatched,
                updated_at    = datetime('now')
        """, (
            game, program, pokemon_name,
            int(encountered_delta), int(caught_delta), int(shinies_delta), int(eggs_hatched_delta)
        ))
        conn.commit()

def get_program_totals(game: str, program: str, db_file: str = DATABASE_PATH) -> Optional[dict]:
    with sqlite3.connect(db_file, timeout=5) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM program_stats WHERE game=? AND program=?", (game, program))
        row = cur.fetchone()
        return dict(row) if row else None

def get_pokemon_totals(game: str, program: str, pokemon_name: str, db_file: str = DATABASE_PATH) -> Optional[dict]:
    with sqlite3.connect(db_file, timeout=5) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM pokemon_stats WHERE game=? AND program=? AND pokemon_name=?",
            (game, program, pokemon_name),
        )
        row = cur.fetchone()
        return dict(row) if row else None

def format_hms(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

class Persistance:
    def _atomic_write_json(path: str, data: dict) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)  # atomic on Windows & POSIX

    def load_json(path: str) -> dict | None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception:
            # corrupted file: keep it for inspection, but ignore it
            return None

    def slot_key(box: int, row: int, col: int) -> str:
        return f"{int(box)}:{int(row)}:{int(col)}"

    def parse_slot_key(k: str) -> tuple[int, int, int]:
        b, r, c = k.split(":")
        return int(b), int(r), int(c)

    def now_iso_utc() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    def sorter_to_cache(image) -> dict[str, Any]:
        s = getattr(image, "sorter", None)
        if not isinstance(s, dict):
            return {}

        # expect:
        # s["slot_to_uid"]: dict[SlotKey(str), int|None]  OR dict[SlotTuple, ...]
        # s["mons"]: dict[int, {...}]
        # s["desired_uid_at"]: dict[SlotKey, int|None]

        cache = {
            "version": 1,
            "game": getattr(image, "game", ""),
            "program": "Box_Sorter",
            "created_at": s.get("created_at") or Persistance.now_iso_utc(),
            "phase": s.get("phase", "scan"),
            "box_count": int(s.get("box_count", 0)),
            "rows": int(s.get("rows", 5)),
            "cols": int(s.get("cols", 6)),

            "scan_progress": {
                "box": int(s.get("scan_box", 0)),
                "row": int(s.get("scan_row", 0)),
                "col": int(s.get("scan_col", 0)),
            },
            "sort_progress": {
                "target_index": int(s.get("target_index", 0)),
                "empty_slot": s.get("empty_slot", None),  # already slot_key string
            },

            "slot_to_uid": s.get("slot_to_uid", {}),
            "mons": s.get("mons", {}),
            "desired_uid_at": s.get("desired_uid_at", {}),
        }
        return cache

    def cache_to_sorter(image, cache: dict) -> dict:
        # basic validation
        if not isinstance(cache, dict) or cache.get("version") != 1:
            return {}
        if cache.get("game") != getattr(image, "game", None):
            return {}

        s = {
            "created_at": cache.get("created_at") or Persistance.now_iso_utc(),
            "phase": cache.get("phase", "scan"),
            "box_count": int(cache.get("box_count", 0)),
            "rows": int(cache.get("rows", 5)),
            "cols": int(cache.get("cols", 6)),

            "scan_box": int(cache.get("scan_progress", {}).get("box", 0)),
            "scan_row": int(cache.get("scan_progress", {}).get("row", 0)),
            "scan_col": int(cache.get("scan_progress", {}).get("col", 0)),

            "target_index": int(cache.get("sort_progress", {}).get("target_index", 0)),
            "empty_slot": cache.get("sort_progress", {}).get("empty_slot", None),

            "slot_to_uid": cache.get("slot_to_uid", {}) or {},
            "mons": cache.get("mons", {}) or {},
            "desired_uid_at": cache.get("desired_uid_at", {}) or {},
        }
        return s

    def save_sorter(image, CACHE_PATH: str):
        cache = Persistance.sorter_to_cache(image)
        if cache:
            Persistance._atomic_write_json(CACHE_PATH, cache)

    def load_sorter(image, CACHE_PATH: str):
        cache = Persistance.load_json(CACHE_PATH)
        if cache:
            image.sorter = Persistance.cache_to_sorter(image, cache)