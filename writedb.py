import os
import sqlite3
import argparse
import bcrypt

def create_database(db_file):
    # Ensure the file extension is .db
    if not db_file.lower().endswith('.db'):
        db_file += '.db'

    # Connect to the SQLite database (or create it if it doesn't exist)
    conn = sqlite3.connect(db_file)

    # Create a cursor object
    cursor = conn.cursor()

    # Turn off foreign keys constraint for the transaction
    cursor.execute("PRAGMA foreign_keys = off;")

    # Begin the transaction
    cursor.execute("BEGIN TRANSACTION;")

    # Drop tables if they exist
    tables = [
        "accounts", "addresses", "clubs", "coaches", "divisions", "matches",
        "player_match_stats", "players", "points", "positions", "teams", "tournaments", "venues"
    ]

    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table};")

    # Create tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT    UNIQUE NOT NULL,
        password TEXT    NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS addresses (
        address_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        street_address TEXT    NOT NULL,
        city           TEXT    NOT NULL,
        state          TEXT    NOT NULL,
        zip_code       TEXT    NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clubs (
        club_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        club_name    TEXT    NOT NULL UNIQUE,
        club_contact TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS coaches (
        coach_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        coach_name    TEXT    NOT NULL,
        coach_contact TEXT    UNIQUE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS divisions (
        division_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        division_name TEXT    NOT NULL UNIQUE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        match_id        INTEGER PRIMARY KEY AUTOINCREMENT,
        match_date      DATE    NOT NULL,
        match_time      TIME    NOT NULL,
        home_team_id    INTEGER NOT NULL,
        away_team_id    INTEGER NOT NULL,
        home_team_score INTEGER,
        away_team_score INTEGER,
        tournament_id   INTEGER,
        venue_id        INTEGER,
        FOREIGN KEY (home_team_id) REFERENCES teams (team_id),
        FOREIGN KEY (away_team_id) REFERENCES teams (team_id),
        FOREIGN KEY (tournament_id) REFERENCES tournaments (tournament_id),
        FOREIGN KEY (venue_id) REFERENCES venues (venue_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS player_match_stats (
        match_id      INTEGER NOT NULL,
        player_id     INTEGER NOT NULL,
        points_scored INTEGER DEFAULT 0,
        position_1_id INTEGER NOT NULL,
        position_2_id INTEGER NOT NULL,
        PRIMARY KEY (match_id, player_id),
        FOREIGN KEY (match_id) REFERENCES matches (match_id),
        FOREIGN KEY (player_id) REFERENCES players (player_id),
        FOREIGN KEY (position_1_id) REFERENCES positions (position_id),
        FOREIGN KEY (position_2_id) REFERENCES positions (position_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS players (
        player_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        player_name    TEXT    NOT NULL,
        date_of_birth  DATE,
        team_id        INTEGER,
        address_id     INTEGER,
        FOREIGN KEY (team_id) REFERENCES teams (team_id),
        FOREIGN KEY (address_id) REFERENCES addresses (address_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS positions (
        position_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        position_name TEXT    NOT NULL UNIQUE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS teams (
        team_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        team_name   TEXT    NOT NULL UNIQUE,
        club_id     INTEGER NOT NULL,
        division_id INTEGER NOT NULL,
        coach_id    INTEGER,
        FOREIGN KEY (club_id) REFERENCES clubs (club_id),
        FOREIGN KEY (division_id) REFERENCES divisions (division_id),
        FOREIGN KEY (coach_id) REFERENCES coaches (coach_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tournaments (
        tournament_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        tournament_name TEXT    NOT NULL UNIQUE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS venues (
        venue_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        venue_name     TEXT    NOT NULL UNIQUE,
        venue_location TEXT    NOT NULL
    );
    """)

    # Commit the transaction
    cursor.execute("COMMIT TRANSACTION;")

    # Turn foreign keys constraint back on
    cursor.execute("PRAGMA foreign_keys = on;")
    hashed = bcrypt.hashpw('admin'.encode('utf-8'), bcrypt.gensalt())
    hashed_pass = hashed.decode('utf-8')

    cursor.execute("INSERT INTO accounts (id, username, password) VALUES (0, 'admin', ?)", (hashed_pass,))
    cursor.execute("INSERT INTO divisions (division_id, division_name) VALUES (0, 'N/A')")
    cursor.execute("INSERT INTO coaches (coach_id, coach_name) VALUES (0, 'N/A')")
    cursor.execute("INSERT INTO positions (position_id, position_name) VALUES (0, 'N/A')")
    
    cursor.execute("DELETE FROM sqlite_sequence")
    
    conn.commit()
    conn.close()
    
    print(f"Database '{db_file}' and tables created successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a SQLite database with specified tables.")
    parser.add_argument("db_file", help="The SQLite database file name.")
    
    args = parser.parse_args()
    create_database(args.db_file)
