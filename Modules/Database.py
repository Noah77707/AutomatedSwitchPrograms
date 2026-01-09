import os
import sqlite3
from typing import Optional

DATABASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Media", "Database.db"))

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
                actions INTEGER NOT NULL DEFAULT 0,
                action_hits INTEGER NOT NULL DEFAULT 0,

                eggs_collected INTEGER NOT NULL DEFAULT 0,
                eggs_hatched INTEGER NOT NULL DEFAULT 0,

                pokemon_encountered INTEGER NOT NULL DEFAULT 0,
                pokemon_caught INTEGER NOT NULL DEFAULT 0,
                pokemon_released INTEGER NOT NULL DEFAULT 0,

                shinies INTEGER NOT NULL DEFAULT 0,
                playtime_seconds INTEGER NOT NULL DEFAULT 0,

                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),

                PRIMARY KEY (game, program)
            )
        """)

        # Per-pokemon totals (only used when a program actually encounters pokemon)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pokemon_stats (
                game TEXT NOT NULL,
                program TEXT NOT NULL,
                pokemon_name TEXT NOT NULL,

                encountered INTEGER NOT NULL DEFAULT 0,
                caught INTEGER NOT NULL DEFAULT 0,
                shinies INTEGER NOT NULL DEFAULT 0,

                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),

                PRIMARY KEY (game, program, pokemon_name),

                FOREIGN KEY (game, program)
                REFERENCES program_stats(game, program)
                ON DELETE CASCADE
            )
        """)

        cur.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_stats_game_program ON pokemon_stats(game, program)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_program_stats_game ON program_stats(game)")

        # Rollup triggers: pokemon_stats -> program_stats (pokemon-only fields)
        cur.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_pokemon_stats_ai
            AFTER INSERT ON pokemon_stats
            BEGIN
                UPDATE program_stats
                SET
                    pokemon_encountered = pokemon_encountered + NEW.encountered,
                    pokemon_caught      = pokemon_caught      + NEW.caught,
                    shinies             = shinies             + NEW.shinies,
                    updated_at          = datetime('now')
                WHERE game = NEW.game AND program = NEW.program;
            END;
        """)

        cur.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_pokemon_stats_au
            AFTER UPDATE ON pokemon_stats
            BEGIN
                UPDATE program_stats
                SET
                    pokemon_encountered = pokemon_encountered + (NEW.encountered - OLD.encountered),
                    pokemon_caught      = pokemon_caught      + (NEW.caught      - OLD.caught),
                    shinies             = shinies             + (NEW.shinies     - OLD.shinies),
                    updated_at          = datetime('now')
                WHERE game = NEW.game AND program = NEW.program;
            END;
        """)

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
    actions_delta: int = 0,
    action_hits_delta: int = 0,
    resets_delta: int = 0,
    eggs_collected_delta: int = 0,
    eggs_hatched_delta: int = 0,
    pokemon_released_delta: int = 0,
    playtime_seconds_delta: int = 0,
    db_file: str = DATABASE_PATH,
) -> None:
    if not game or not program:
        raise ValueError("game and program are required")
    if any(d < 0 for d in (
        actions_delta, action_hits_delta, resets_delta,
        eggs_collected_delta, eggs_hatched_delta, pokemon_released_delta,
        playtime_seconds_delta
    )):
        raise ValueError("deltas must be >= 0")
    if all(d == 0 for d in (
        actions_delta, action_hits_delta, resets_delta,
        eggs_collected_delta, eggs_hatched_delta, pokemon_released_delta,
        playtime_seconds_delta
    )):
        return

    ensure_program_row(game, program, db_file=db_file)

    with sqlite3.connect(db_file, timeout=5) as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE program_stats
            SET
                actions = actions + ?,
                action_hits = action_hits + ?,
                resets = resets + ?,
                eggs_collected = eggs_collected + ?,
                eggs_hatched = eggs_hatched + ?,
                pokemon_released = pokemon_released + ?,
                playtime_seconds = playtime_seconds + ?,
                updated_at = datetime('now')
            WHERE game = ? AND program = ?
        """, (
            int(actions_delta),
            int(action_hits_delta),
            int(resets_delta),
            int(eggs_collected_delta),
            int(eggs_hatched_delta),
            int(pokemon_released_delta),
            int(playtime_seconds_delta),
            game, program
        ))
        conn.commit()

def finish_program_run(
    game: str,
    program: str,
    *,
    db_file: str = DATABASE_PATH,
) -> None:
    """Increment runs by 1 at end of a run (works for all programs)."""
    ensure_program_row(game, program, db_file=db_file)
    with sqlite3.connect(db_file, timeout=5) as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE program_stats
            SET runs = runs + 1,
                updated_at = datetime('now')
            WHERE game = ? AND program = ?
        """, (game, program))
        conn.commit()

def add_pokemon_delta(
    game: str,
    program: str,
    pokemon_name: str,
    *,
    encountered_delta: int = 0,
    caught_delta: int = 0,
    shinies_delta: int = 0,
    db_file: str = DATABASE_PATH,
) -> None:
    if not game or not program or not pokemon_name:
        raise ValueError("game, program, pokemon_name are required")
    if any(d < 0 for d in (encountered_delta, caught_delta, shinies_delta)):
        raise ValueError("deltas must be >= 0")
    if encountered_delta == 0 and caught_delta == 0 and shinies_delta == 0:
        return

    # Ensure program row exists for FK
    ensure_program_row(game, program, db_file=db_file)

    with sqlite3.connect(db_file, timeout=5) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO pokemon_stats (game, program, pokemon_name, encountered, caught, shinies)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(game, program, pokemon_name) DO UPDATE SET
                encountered = encountered + excluded.encountered,
                caught      = caught      + excluded.caught,
                shinies     = shinies     + excluded.shinies,
                updated_at  = datetime('now')
        """, (game, program, pokemon_name, int(encountered_delta), int(caught_delta), int(shinies_delta)))
        conn.commit()

# ----------------------------
# Reads
# ----------------------------
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
