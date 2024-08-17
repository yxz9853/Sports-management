import bcrypt
import sqlite3
import random
import subprocess
from datetime import datetime, timedelta
from lists import first_names, last_names, animals, adjectives, nouns

def random_string(length=8):
    letters = 'abcdefghijklmnopqrstuvwxyz'
    return ''.join(random.choice(letters) for i in range(length))

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), password

def random_date(start, end):
    return start + timedelta(days=random.randint(0, (end - start).days))

def generate_data(db_name, num_players, num_teams, num_clubs, output_file):
    # Run writedb.py with the db parameter
    subprocess.run(['python', 'writedb.py', db_name])

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Generate players data
    players_data = [
        (
            i, 
            f'{random.choice(first_names)} {random.choice(last_names)}', 
            random_date(datetime(2000, 1, 1), datetime(2010, 12, 31)).strftime('%Y-%m-%d'),
            None, random.randint(1, 101)
        ) 
        for i in range(1, num_players + 1)
    ]
    cursor.executemany("INSERT INTO players (player_id, player_name, date_of_birth, team_id, address_id) VALUES (?, ?, ?, ?, ?);", players_data)

    # Generate unique club names using adjectives and nouns
    used_club_names = set()
    clubs_data = []
    for i in range(1, num_clubs + 1):
        while True:
            club_name = f'{random.choice(adjectives)} {random.choice(nouns)}'
            if club_name not in used_club_names:
                used_club_names.add(club_name)
                clubs_data.append((i, club_name, f'contact_{i}@club.com'))
                break
    cursor.executemany("INSERT INTO clubs (club_id, club_name, club_contact) VALUES (?, ?, ?);", clubs_data)

    # Generate accounts with the same number as clubs
    accounts_data = [
        (i, f'user_{i}', *hash_password(random_string(12))) 
        for i in range(1, num_clubs + 1)
    ]
    accounts_data_sliced = [(i, username, password) for (i, username, password, *rest) in accounts_data]
    cursor.executemany("INSERT INTO accounts (id, username, password) VALUES (?, ?, ?);", accounts_data_sliced)

    with open(output_file, 'w') as f:
        for i, username, hashed, password in accounts_data:
            f.write(f"{username}: {password}\n")

    # Generate unique team names using adjectives and animals
    used_team_names = set()
    teams_data = []
    for i in range(1, num_teams + 1):
        while True:
            team_name = f'{random.choice(adjectives)} {random.choice(animals)}'
            if team_name not in used_team_names:
                used_team_names.add(team_name)
                teams_data.append((i, team_name, i % num_clubs + 1, random.randint(1, 20), random.randint(1, 20)))
                break
    cursor.executemany("INSERT INTO teams (team_id, team_name, club_id, division_id, coach_id) VALUES (?, ?, ?, ?, ?);", teams_data)

    # Insert data into the remaining tables
    addresses_data = [
        (i, f'{i} Main St', f'City_{i}', f'State_{i}', f'{random.randint(10000, 99999)}') 
        for i in range(1, 101)
    ]
    cursor.executemany("INSERT INTO addresses (address_id, street_address, city, state, zip_code) VALUES (?, ?, ?, ?, ?);", addresses_data)

    coaches_data = [
        (i, f'Coach_{i}', f'{random.randint(1000000000, 9999999999)}') 
        for i in range(1, num_clubs * 2 + 1)
    ]
    cursor.executemany("INSERT INTO coaches (coach_id, coach_name, coach_contact) VALUES (?, ?, ?);", coaches_data)

    # Assign players to teams ensuring no team has more than 10 players
    team_players = {i: [] for i in range(1, num_teams + 1)}
    player_ids = list(range(1, num_players + 1))
    random.shuffle(player_ids)

    for player_id in player_ids:
        available_teams = [team_id for team_id, players in team_players.items() if len(players) < 10]
        if available_teams:
            team_id = random.choice(available_teams)
            team_players[team_id].append(player_id)
            cursor.execute("UPDATE players SET team_id = ? WHERE player_id = ?", (team_id, player_id))

    # Generate matches data
    matches_data = []
    team_ids_with_players = set(team_players.keys())

    for i in range(1, num_teams * 10 + 1):
        home_team_id = random.choice(list(team_ids_with_players))
        away_team_id = random.choice(list(team_ids_with_players))
        
        home_team_score = random.randint(1, 100)
        away_team_score = random.randint(1, 100)

        matches_data.append(
            (
                i, 
                random_date(datetime(2023, 1, 1), datetime(2024, 1, 1)).strftime('%Y-%m-%d'), 
                f'{random.randint(12, 23)}:{random.randint(0, 59):02}',
                home_team_id, away_team_id, home_team_score, away_team_score,
                random.randint(1, 20), random.randint(1, 20)
            )
        )
    cursor.executemany("INSERT INTO matches (match_id, match_date, match_time, home_team_id, away_team_id, home_team_score, away_team_score, tournament_id, venue_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);", matches_data)

    unique_match_player_pairs = set()

    def distribute_points(total_points, num_players):
        points_distribution = [0] * num_players
        for _ in range(total_points):
            random_player = random.randint(0, num_players - 1)
            points_distribution[random_player] += 1
        return points_distribution

    player_match_stats_data = []
    for match in matches_data:
        match_id = match[0]
        home_team_id = match[3]
        away_team_id = match[4]
        home_team_score = match[5]
        away_team_score = match[6]
        
        home_players = team_players[home_team_id]
        if home_players:
            home_player_points = distribute_points(home_team_score, len(home_players))
            for player_id, points in zip(home_players, home_player_points):
                pair = (match_id, player_id)
                if pair not in unique_match_player_pairs:
                    unique_match_player_pairs.add(pair)
                    player_match_stats_data.append((match_id, player_id, points, random.randint(1, 20), random.randint(1, 20)))

        away_players = team_players[away_team_id]
        if away_players:
            away_player_points = distribute_points(away_team_score, len(away_players))
            for player_id, points in zip(away_players, away_player_points):
                pair = (match_id, player_id)
                if pair not in unique_match_player_pairs:
                    unique_match_player_pairs.add(pair)
                    player_match_stats_data.append((match_id, player_id, points, random.randint(1, 20), random.randint(1, 20)))

    cursor.executemany("INSERT INTO player_match_stats (match_id, player_id, points_scored, position_1_id, position_2_id) VALUES (?, ?, ?, ?, ?);", player_match_stats_data)

    divisions_data = [(i, f'Division_{i}') for i in range(1, 21)]
    cursor.executemany("INSERT INTO divisions (division_id, division_name) VALUES (?, ?);", divisions_data)

    positions_data = [(i, f'Position_{i}') for i in range(1, 21)]
    cursor.executemany("INSERT INTO positions (position_id, position_name) VALUES (?, ?);", positions_data)

    tournaments_data = [(i, f'Tournament_{i}') for i in range(1, 21)]
    cursor.executemany("INSERT INTO tournaments (tournament_id, tournament_name) VALUES (?, ?);", tournaments_data)

    venues_data = [(i, f'Venue_{i}', f'Location_{i}') for i in range(1, 21)]
    cursor.executemany("INSERT INTO venues (venue_id, venue_name, venue_location) VALUES (?, ?, ?);", venues_data)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate test data for the database.")
    parser.add_argument("db_name", help="The name of the database file.")
    parser.add_argument("num_players", type=int, help="The number of players to generate.")
    parser.add_argument("num_teams", type=int, help="The number of teams to generate.")
    parser.add_argument("num_clubs", type=int, help="The number of clubs and accounts to generate.")
    parser.add_argument("output_file", help="The file to output the usernames and passwords.")

    args = parser.parse_args()

    generate_data(args.db_name, args.num_players, args.num_teams, args.num_clubs, args.output_file)
