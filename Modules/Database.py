import os, sqlite3, json, time
from typing import Optional, Any

DATABASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Media", "Database.db"))


def _ensure_column(cur: sqlite3.Cursor, table: str, col_def_sql: str) -> None:
    """
    Adds a column if missing. col_def_sql example:
    "skipped INTEGER NOT NULL DEFAULT 0"
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

        # ---- Legacy aggregate totals table (kept for compatibility) ----
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
                hatched INTEGER NOT NULL DEFAULT 0,

                encountered INTEGER NOT NULL DEFAULT 0,
                caught INTEGER NOT NULL DEFAULT 0,
                released INTEGER NOT NULL DEFAULT 0,
                skipped INTEGER NOT NULL DEFAULT 0,

                shinies INTEGER NOT NULL DEFAULT 0,
                playtime_seconds INTEGER NOT NULL DEFAULT 0,

                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),

                PRIMARY KEY (game, program)
            )
        """)

        _ensure_column(cur, "program_stats", "encounters INTEGER NOT NULL DEFAULT 0")
        _ensure_column(cur, "program_stats", "skipped INTEGER NOT NULL DEFAULT 0")

        # ---- Legacy aggregate per-pokemon totals (kept for compatibility) ----
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                game TEXT NOT NULL,
                program TEXT NOT NULL,
                name TEXT NOT NULL,

                encountered INTEGER NOT NULL DEFAULT 0,
                caught INTEGER NOT NULL DEFAULT 0,
                shinies INTEGER NOT NULL DEFAULT 0,
                hatched INTEGER NOT NULL DEFAULT 0,
                released INTEGER NOT NULL DEFAULT 0,

                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),

                PRIMARY KEY (game, program, name),

                FOREIGN KEY (game, program)
                REFERENCES program_stats(game, program)
                ON DELETE CASCADE
            )
        """)
        _ensure_column(cur, "stats", "hatched INTEGER NOT NULL DEFAULT 0")

        # ---- NEW: one row per run instance ----
        cur.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game TEXT NOT NULL,
                program TEXT NOT NULL,

                started_at TEXT NOT NULL DEFAULT (datetime('now')),
                ended_at TEXT,
                status TEXT NOT NULL DEFAULT 'running', -- running|completed|failed|aborted

                resets INTEGER NOT NULL DEFAULT 0,
                encounters INTEGER NOT NULL DEFAULT 0,
                actions INTEGER NOT NULL DEFAULT 0,
                action_hits INTEGER NOT NULL DEFAULT 0,

                eggs_collected INTEGER NOT NULL DEFAULT 0,
                hatched INTEGER NOT NULL DEFAULT 0,

                encountered INTEGER NOT NULL DEFAULT 0,
                caught INTEGER NOT NULL DEFAULT 0,
                released INTEGER NOT NULL DEFAULT 0,
                skipped INTEGER NOT NULL DEFAULT 0,

                shinies INTEGER NOT NULL DEFAULT 0,
                playtime_seconds INTEGER NOT NULL DEFAULT 0
            )
        """)

        # ---- NEW: per-pokemon-per-run totals ----
        cur.execute("""
            CREATE TABLE IF NOT EXISTS run_stats (
                run_id INTEGER NOT NULL,
                name TEXT NOT NULL,

                encountered INTEGER NOT NULL DEFAULT 0,
                caught INTEGER NOT NULL DEFAULT 0,
                shinies INTEGER NOT NULL DEFAULT 0,
                hatched INTEGER NOT NULL DEFAULT 0,
                released INTEGER NOT NULL DEFAULT 0,

                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),

                PRIMARY KEY (run_id, name),
                FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
            )
        """)

        # Optional event log for full audit trail (you can remove if you don't need it)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS run_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                ts TEXT NOT NULL DEFAULT (datetime('now')),
                event_type TEXT NOT NULL,            -- encounter|catch|reset|etc
                name TEXT,
                value INTEGER NOT NULL DEFAULT 1,
                payload_json TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
            )
        """)

        cur.execute("CREATE INDEX IF NOT EXISTS idx_program_stats_game ON program_stats(game)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_stats_game_program ON stats(game, program)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_runs_game_program ON runs(game, program)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_run_name ON run_stats(name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_run_events_run_id ON run_events(run_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_run_events_type ON run_events(event_type)")

        # IMPORTANT: remove old rollup triggers to prevent double counting
        cur.execute("DROP TRIGGER IF EXISTS trg_stats_ai;")
        cur.execute("DROP TRIGGER IF EXISTS trg_stats_au;")

        conn.commit()

# Old Backwards-compatible functions for legacy aggregate totals (kept for compatibility with old code)
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
    hatched_delta: int = 0,
    encountered_delta: int = 0,
    caught_delta: int = 0,
    released_delta: int = 0,
    skipped_delta: int = 0,
    shinies_delta: int = 0,
    playtime_seconds_delta: int = 0,
    db_file: str = DATABASE_PATH,
) -> None:
    if not game or not program:
        raise ValueError("game and program are required")

    deltas = (
        runs_delta, resets_delta, encounters_delta,
        actions_delta, action_hits_delta,
        eggs_collected_delta, hatched_delta,
        encountered_delta, caught_delta,
        released_delta, skipped_delta,
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
                hatched = hatched + ?,
                encountered = encountered + ?,
                caught = caught + ?,
                released = released + ?,
                skipped = skipped + ?,
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
                int(hatched_delta),
                int(encountered_delta),
                int(caught_delta),
                int(released_delta),
                int(skipped_delta),
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
    name: str,
    *,
    encountered_delta: int = 0,
    caught_delta: int = 0,
    shinies_delta: int = 0,
    hatched_delta: int = 0,
    released_delta: int = 0,
    db_file: str = DATABASE_PATH,
) -> None:
    if not game or not program or not name:
        raise ValueError("game, program, name are required")
    if any(d < 0 for d in (encountered_delta, caught_delta, shinies_delta, hatched_delta, released_delta)):
        raise ValueError("deltas must be >= 0")
    if all(d == 0 for d in (encountered_delta, caught_delta, shinies_delta, hatched_delta, released_delta)):
        return

    ensure_program_row(game, program, db_file=db_file)

    with sqlite3.connect(db_file, timeout=5) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO stats (
                game, program, name,
                encountered, caught, shinies, hatched, released
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(game, program, name) DO UPDATE SET
                encountered   = encountered   + excluded.encountered,
                caught        = caught        + excluded.caught,
                shinies       = shinies       + excluded.shinies,
                hatched       = hatched       + excluded.hatched,
                released      = released      + excluded.released,
                updated_at    = datetime('now')
        """, (
            game, program, name,
            int(encountered_delta), int(caught_delta), int(shinies_delta), int(hatched_delta), int(released_delta)
        ))
        conn.commit()

# New Run based functions (preferred for new code)
def start_run(game: str, program: str, db_file: str = DATABASE_PATH) -> int:
    if not game or not program:
        raise ValueError("game and program are required")

    # keep legacy program row alive too (optional but useful if you still read old tables)
    ensure_program_row(game, program, db_file=db_file)

    with sqlite3.connect(db_file, timeout=5) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO runs (game, program, started_at, status)
            VALUES (?, ?, datetime('now'), 'running')
        """, (game, program))
        conn.commit()
        return int(cur.lastrowid)

def end_run(run_id: int, status: str = "completed", db_file: str = DATABASE_PATH) -> None:
    if status not in {"running", "completed", "failed", "aborted"}:
        raise ValueError("status must be one of: running, completed, failed, aborted")

    with sqlite3.connect(db_file, timeout=5) as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE runs
            SET ended_at = datetime('now'),
                status = ?
            WHERE id = ?
        """, (status, int(run_id)))
        conn.commit()

def add_run_deltas(
    run_id: int,
    *,
    resets_delta: int = 0,
    encounters_delta: int = 0,
    actions_delta: int = 0,
    action_hits_delta: int = 0,
    eggs_collected_delta: int = 0,
    hatched_delta: int = 0,
    encountered_delta: int = 0,
    caught_delta: int = 0,
    released_delta: int = 0,
    skipped_delta: int = 0,
    shinies_delta: int = 0,
    playtime_seconds_delta: int = 0,
    db_file: str = DATABASE_PATH,
) -> None:
    deltas = (
        resets_delta, encounters_delta, actions_delta, action_hits_delta,
        eggs_collected_delta, hatched_delta,
        encountered_delta, caught_delta, released_delta,
        skipped_delta, shinies_delta, playtime_seconds_delta,
    )
    if any(d < 0 for d in deltas):
        raise ValueError("deltas must be >= 0")
    if all(d == 0 for d in deltas):
        return

    with sqlite3.connect(db_file, timeout=5) as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE runs
            SET
                resets = resets + ?,
                encounters = encounters + ?,
                actions = actions + ?,
                action_hits = action_hits + ?,
                eggs_collected = eggs_collected + ?,
                hatched = hatched + ?,
                encountered = encountered + ?,
                caught = caught + ?,
                released = released + ?,
                skipped = skipped + ?,
                shinies = shinies + ?,
                playtime_seconds = playtime_seconds + ?
            WHERE id = ?
        """, (
            int(resets_delta),
            int(encounters_delta),
            int(actions_delta),
            int(action_hits_delta),
            int(eggs_collected_delta),
            int(hatched_delta),
            int(encountered_delta),
            int(caught_delta),
            int(released_delta),
            int(skipped_delta),
            int(shinies_delta),
            int(playtime_seconds_delta),
            int(run_id),
        ))
        conn.commit()

def add_run_pokemon_delta(
    run_id: int,
    name: str,
    *,
    encountered_delta: int = 0,
    caught_delta: int = 0,
    shinies_delta: int = 0,
    hatched_delta: int = 0,
    released_delta: int = 0,
    db_file: str = DATABASE_PATH,
) -> None:
    if not run_id or not name:
        raise ValueError("run_id and name are required")
    if any(d < 0 for d in (encountered_delta, caught_delta, shinies_delta, hatched_delta, released_delta)):
        raise ValueError("deltas must be >= 0")
    if all(d == 0 for d in (encountered_delta, caught_delta, shinies_delta, hatched_delta, released_delta)):
        return

    with sqlite3.connect(db_file, timeout=5) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO run_stats (
                run_id, name, encountered, caught, shinies, hatched, released
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id, name) DO UPDATE SET
                encountered  = encountered + excluded.encountered,
                caught       = caught + excluded.caught,
                shinies      = shinies + excluded.shinies,
                hatched = hatched + excluded.hatched,
                released     = released + excluded.released,
                updated_at   = datetime('now')
        """, (
            int(run_id),
            name,
            int(encountered_delta),
            int(caught_delta),
            int(shinies_delta),
            int(hatched_delta),
            int(released_delta),
        ))
        conn.commit()

def log_run_event(
    run_id: int,
    event_type: str,
    *,
    name: Optional[str] = None,
    value: int = 1,
    payload: Optional[dict] = None,
    db_file: str = DATABASE_PATH
) -> None:
    if not event_type:
        raise ValueError("event_type is required")
    if value < 0:
        raise ValueError("value must be >= 0")

    with sqlite3.connect(db_file, timeout=5) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO run_events (run_id, event_type, name, value, payload_json)
            VALUES (?, ?, ?, ?, ?)
        """, (
            int(run_id),
            event_type,
            name,
            int(value),
            json.dumps(payload, ensure_ascii=False) if payload is not None else None
        ))
        conn.commit()

def get_program_totals(game: str, program: str, db_file: str = DATABASE_PATH) -> Optional[dict]:
    with sqlite3.connect(db_file, timeout=5) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM program_stats WHERE game=? AND program=?", (game, program))
        row = cur.fetchone()
        return dict(row) if row else None

def get_totals(game: str, program: str, name: str, db_file: str = DATABASE_PATH) -> Optional[dict]:
    with sqlite3.connect(db_file, timeout=5) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM stats WHERE game=? AND program=? AND name=?",
            (game, program, name),
        )
        row = cur.fetchone()
        return dict(row) if row else None

def get_run(run_id: int, db_file: str = DATABASE_PATH) -> Optional[dict]:
    with sqlite3.connect(db_file, timeout=5) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM runs WHERE id=?", (int(run_id),))
        row = cur.fetchone()
        return dict(row) if row else None

def get_run_totals(run_id: int, name: str, db_file: str = DATABASE_PATH) -> Optional[dict]:
    with sqlite3.connect(db_file, timeout=5) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM run_stats
            WHERE run_id=? AND name=?
        """, (int(run_id), name))
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
                "empty_slot": s.get("empty_slot", None),
            },
            "slot_to_uid": s.get("slot_to_uid", {}),
            "mons": s.get("mons", {}),
            "desired_uid_at": s.get("desired_uid_at", {}),
        }
        return cache

    def cache_to_sorter(image, cache: dict) -> dict:
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

