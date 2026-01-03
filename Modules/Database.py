import os
import sys
import sqlite3
from typing import Dict, Union, Tuple, List, Optional

import Constants as const

DATABASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Media', 'Database.db'))

NEW_INT_COLS = [
    ("resets", 0),
    ("pokemon_encountered", 0),
    ("pokemon_caught", 0),
    ("eggs_collected", 0),
    ("eggs_hatched", 0),
    ("pokemon_released", 0),
    ("action_hit", 0)
]

def _add_missing_columns(cur: sqlite3.Cursor, table: str) -> None:
    cur.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cur.fetchall()}  # column name

    for col, default in NEW_INT_COLS:
        if col not in existing:
            cur.execute(
                f"ALTER TABLE {table} ADD COLUMN {col} INTEGER NOT NULL DEFAULT {int(default)}"
            )

def initialize_database(db_file: str = DATABASE_PATH) -> None:
    with sqlite3.connect(db_file) as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute("PRAGMA synchronous=NORMAL;")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS program_stats (
                game TEXT NOT NULL,
                program TEXT NOT NULL,

                runs INTEGER NOT NULL DEFAULT 0,
                action INTEGER NOT NULL DEFAULT 0,
                resets INTEGER NOT NULL DEFAULT 0,
                pokemon_encountered INTEGER NOT NULL DEFAULT 0,
                pokemon_caught INTEGER NOT NULL DEFAULT 0,
                eggs_collected INTEGER NOT NULL DEFAULT 0,
                eggs_hatched INTEGER NOT NULL DEFAULT 0,
                pokemon_released INTEGER NOT NULL DEFAULT 0,

                shinies INTEGER NOT NULL DEFAULT 0,
                action_hit INTEGER NOT NULL DEFAULT 0,
                playtime_seconds INTEGER NOT NULL DEFAULT 0,

                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),

                PRIMARY KEY (game, program)
            )
        """)
        _add_missing_columns(cur, "program_stats")

        cur.execute("CREATE INDEX IF NOT EXISTS idx_program_stats_game ON program_stats(game)")
        conn.commit()

def add_deltas(
    game: str,
    program: str,
    *,
    action_delta: int = 0,
    resets_delta: int = 0,
    pokemon_encountered_delta: int = 0,
    pokemon_caught_delta: int = 0,
    eggs_collected_delta: int = 0,
    eggs_hatched_delta: int = 0,
    pokemon_released_delta: int = 0,
    shinies_delta: int = 0,
    action_hit_delta: int = 0,

    playtime_seconds_delta: int = 0,
    db_file: str = DATABASE_PATH,
) -> None:
    if not game or not program:
        raise ValueError("game and program are required")
    if min(action_delta, shinies_delta, playtime_seconds_delta) < 0:
        raise ValueError("deltas must be >= 0")

    if all(d == 0 for d in (
        action_delta, resets_delta, pokemon_encountered_delta, pokemon_caught_delta,
        eggs_collected_delta, eggs_hatched_delta, pokemon_released_delta,
        shinies_delta, action_hit_delta, playtime_seconds_delta
    )):
        return


    with sqlite3.connect(db_file, timeout=5) as conn:
        cur = conn.cursor()
        # ensure row exists
        cur.execute("""
            INSERT INTO program_stats (game, program)
            VALUES (?, ?)
            ON CONFLICT(game, program) DO NOTHING
        """, (game, program))

        cur.execute("""
            UPDATE program_stats
            SET
                action = action + ?,
                resets = resets + ?,
                pokemon_encountered = pokemon_encountered + ?,
                pokemon_caught = pokemon_caught + ?,
                eggs_collected = eggs_collected + ?,
                eggs_hatched = eggs_hatched + ?,
                pokemon_released = pokemon_released + ?,
                shinies = shinies + ?,
                action_hit = action_hit + ?,
                playtime_seconds = playtime_seconds + ?,
                updated_at = datetime('now')
            WHERE game = ? AND program = ?
        """, (
            int(action_delta),
            int(resets_delta),
            int(pokemon_encountered_delta),
            int(pokemon_caught_delta),
            int(eggs_collected_delta),
            int(eggs_hatched_delta),
            int(pokemon_released_delta),
            int(shinies_delta),
            int(action_hit_delta),
            int(playtime_seconds_delta),
            game, program
        ))
        conn.commit()

def finish_run(
    game: str,
    program: str,
    *,
    action_delta: int = 0,
    resets_delta: int = 0,
    pokemon_encountered_delta: int = 0,
    pokemon_caught_delta: int = 0,
    eggs_collected_delta: int = 0,
    eggs_hatched_delta: int = 0,
    pokemon_released_delta: int = 0,
    shinies_delta: int = 0,
    action_hit_delta: int = 0,
    playtime_seconds_delta: int = 0,
    db_file: str = DATABASE_PATH,
) -> None:
    if not game or not program:
        raise ValueError("game and program are required")

    deltas = [
        action_delta, resets_delta, pokemon_encountered_delta, pokemon_caught_delta,
        eggs_collected_delta, eggs_hatched_delta, pokemon_released_delta,
        shinies_delta, action_hit_delta, playtime_seconds_delta
    ]
    if any(d < 0 for d in deltas):
        raise ValueError("deltas must be >= 0")

    with sqlite3.connect(db_file, timeout=5) as conn:
        cur = conn.cursor()

        # Ensure columns exist if you are doing migration
        _add_missing_columns(cur, "program_stats")

        cur.execute("""
            INSERT INTO program_stats (
                game, program,
                runs,
                action, resets, pokemon_encountered, pokemon_caught,
                eggs_collected, eggs_hatched, pokemon_released,
                shinies, action_hit, playtime_seconds
            )
            VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(game, program) DO UPDATE SET
                runs = runs + 1,
                action = action + excluded.action,
                resets = resets + excluded.resets,
                pokemon_encountered = pokemon_encountered + excluded.pokemon_encountered,
                pokemon_caught = pokemon_caught + excluded.pokemon_caught,
                eggs_collected = eggs_collected + excluded.eggs_collected,
                eggs_hatched = eggs_hatched + excluded.eggs_hatched,
                pokemon_released = pokemon_released + excluded.pokemon_released,
                shinies = shinies + excluded.shinies,
                action_hit = action_hit + excluded.action_hit,
                playtime_seconds = playtime_seconds + excluded.playtime_seconds,
                updated_at = datetime('now')
        """, (
            game, program,
            int(action_delta),
            int(resets_delta),
            int(pokemon_encountered_delta),
            int(pokemon_caught_delta),
            int(eggs_collected_delta),
            int(eggs_hatched_delta),
            int(pokemon_released_delta),
            int(shinies_delta),
            int(action_hit_delta),
            int(playtime_seconds_delta),
        ))

        conn.commit()

def get_stats(game: str, program: str, db_file: str = DATABASE_PATH) -> Optional[dict]:
    with sqlite3.connect(db_file) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT
                game, program, runs,
                action, resets,
                pokemon_encountered, pokemon_caught,
                eggs_collected, eggs_hatched,
                pokemon_released, shinies, 
                action_hit, playtime_seconds,
                created_at, updated_at
            FROM program_stats
            WHERE game = ? AND program = ?

        """, (game, program))
        row = cur.fetchone()
        return dict(row) if row else None

def format_hms(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"
