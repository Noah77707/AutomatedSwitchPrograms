import os
import sys
import sqlite3
from typing import Dict, Union, Tuple, List

import Constants as const

DATABASE_PATH = os.path.abspath(os.path.join(os.path.dirname), '..', 'Media/Database.db')

def initialize_database(db_file: str = DATABASE_PATH) -> None:
    connection = sqlite3.connect(db_file)
    cursor = connection.cursor()

    cursor.execute('''
        CREATE TABLE General (
            global_encounters Integer,
            global_playtime REAL,
            last_shiny_encounter INTEGER,
            global_shinies_found INTEGER
        )
    ''')

    cursor.execute('''
        CREATE TABLE Pokemon (
                   pokemon_name TEXT NOT NULL
                   shiny_encounters INTEGER,
                   encounters INTEGER
        )        
    ''')

    cursor.execute("SELECT COUNT(*) FROM General")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO General (
                global_encounters, global_playtime, last_shiny_encounter, global_shinies_found
            ) VALUES (?, ?, ?, ?)
            ''', (0, 0.0, 0, 0))
        
    connection.commit()
    connection.close

def add_or_update_encounter(
        pokemon_data: Dict[str, Union[str, bool]],
        local_playtime: float,
        db_files: str = DATABASE_PATH
) -> None:
    
    connection = sqlite3.connect(db_files)
    cursor = connection.cursor()

    cursor.execute("SELECT global_encounters, last_shiny_encounter FROM General")
    global_encounters, last_shiny_encounter = cursor.fetchone()