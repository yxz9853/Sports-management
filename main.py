from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_login import LoginManager, UserMixin, login_user, logout_user
from forms import RegistrationForm
import sqlite3
from functools import wraps
import bcrypt
import os

app = Flask(__name__)
app.secret_key = '123456'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect to the login page if unauthorized

def checklogin(func): # Checks if user is logged in
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('You are not logged in.', 'danger')
            return redirect(url_for('index'))
        return func(*args, **kwargs)
    return wrapper

def checkloginr(func): # Reverse checks and redirects users
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user_id' in session:
            if session['user_role'] == 'admin':
                return redirect(url_for('admin'))
            return redirect(url_for('dashboard'))
        return func(*args, **kwargs)
    return wrapper

def checkadmin(func): # Checks if user is admin
    @wraps(func)
    def wrapper(*args, **kwargs):
        @checklogin
        def inner_wrapper(*args, **kwargs):
            if session['user_role'] != 'admin':
                flash('You are not permitted to access this page.', 'danger')
                return redirect(url_for('dashboard'))
            return func(*args, **kwargs)
        return inner_wrapper(*args, **kwargs)
    return wrapper

def hash_password(password):    # Hash the password with a generated salt
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')

def verify_password(password, stored_hash): # Verify the password against the stored hash
    return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))

# User model
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

app.config['SESSION_CLEARED'] = False

@app.errorhandler(TypeError) # Handles errors
def handle_type_error(e):
    return render_template('error.html'), 400

@app.before_request
def clear_session_on_startup(): # Check if the session has been cleared already
    if not app.config['SESSION_CLEARED']:
        session.clear()
        app.config['SESSION_CLEARED'] = True  # Set the flag

@login_manager.user_loader
def load_user(user_id):
    try:
        with sqlite3.connect(database) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT id, username, password FROM accounts WHERE id = ?", (user_id,))
            row = cur.fetchone()

            if row:
                return User(row['id'], row['username'], row['password'])
            else:
                return None
    except sqlite3.Error as e:
        print(f'Database error: {str(e)}')
        return None

@app.route('/')
@checkloginr
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
@checkloginr
def login():   
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            with sqlite3.connect(database) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT id, username, password FROM accounts WHERE username = ?", (username,))
                row = cur.fetchone()

                if row and verify_password(password, row['password']):
                    user = User(row['id'], row['username'], row['password'])
                    login_user(user)

                    # Set the session variables for the logged-in user
                    session['user_id'] = row['id']
                    session['username'] = row['username']
                    
                    if username == 'admin':
                        session['user_role'] = 'admin'
                    else:
                        session['user_role'] = 'user'

                    # Retrieve the club name for the logged-in user
                    cur.execute("SELECT club_name FROM clubs WHERE club_name = ?", (row['username'],))

                    flash('Logged in successfully.', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    flash('Invalid club name or password.', 'danger')
        except sqlite3.Error as e:
            flash(f'Database error: {str(e)}', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
@checkloginr
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        hashed_pass = hash_password(password)
        try:
            with sqlite3.connect(database) as conn:
                cur = conn.cursor()
                cur.execute("INSERT INTO accounts (username, password) VALUES (?, ?)", (username, hashed_pass))
                cur.execute("INSERT INTO clubs (club_name) VALUES (?)", (username,))
                conn.commit()
                flash(f'{username} has been registered successfully!', 'success')
                return redirect(url_for('index'))
        except sqlite3.IntegrityError:  # Check if club name already exists
            flash('Club already exists. Please check again.', 'danger')
            return render_template('register.html', form=form)
    elif form.errors:   # Check if passwords are matching or other errors are present
        for field, errors in form.errors.items():
            for error in errors:
                if error == 'wrongconf':
                    flash("Please ensure the passwords are the same.", 'danger')
                else:
                    flash(f"{field.capitalize()} field error: {error}", 'danger')

    return render_template('register.html', form=form)

@app.route('/dashboard')
@checklogin
def dashboard():   
    if session['user_role'] == 'admin':
                return redirect(url_for('admin')) 
    return render_template('dashboard.html', club_id=session['user_id'])

@app.route('/admin')
@checkadmin
def admin():
    return render_template('admin.html')

@app.route('/divisions', methods=['GET', 'POST'])
@checkadmin
def divisions():
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute('SELECT * FROM divisions')
    divisions = cur.fetchall()
    conn.close()
    divisions = divisions[1:]
    return render_template('divisions.html', divisions=divisions)

@app.route('/divisions/add', methods=['POST'])
@checkadmin
def add_division():
    division_name = request.form['division_name']
    try:
        conn = sqlite3.connect(database)
        cur = conn.cursor()
        cur.execute('INSERT INTO divisions (division_name) VALUES (?)', (division_name,))
        conn.commit()
        conn.close()
        flash(f'Division {division_name} has been created.', 'success')
        return redirect(url_for('divisions'))
    except sqlite3.IntegrityError:
        flash(f'{division_name} already exists.', 'danger')
        return redirect(url_for('divisions'))

@app.route('/divisions/remove/<int:division_id>', methods=['GET'])
@checkadmin
def remove_division(division_id):
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute('SELECT division_name FROM divisions WHERE division_id = ?', (division_id,))
    division_name = cur.fetchone()[0]
    cur.execute('DELETE FROM divisions WHERE division_id = ?', (division_id,))
    conn.commit()
    conn.close()
    flash(f'{division_name} has been successfully deleted', 'success')
    return redirect(url_for('divisions'))

@app.route('/positions', methods=['GET', 'POST'])
@checkadmin
def positions():
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute('SELECT * FROM positions')
    positions = cur.fetchall()
    conn.close()
    positions = positions[1:]
    return render_template('positions.html', positions=positions)

@app.route('/positions/add', methods=['POST'])
@checkadmin
def add_position():
    if 'user_id' not in session:
        flash('You are not logged in.', 'danger')
        return redirect(url_for('index'))
    if session['user_role'] != 'admin':
        flash('You are not permitted to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    position_name = request.form['position_name']
    try:
        conn = sqlite3.connect(database)
        cur = conn.cursor()
        cur.execute('INSERT INTO positions (position_name) VALUES (?)', (position_name,))
        conn.commit()
        conn.close()
        flash(f'Position {position_name} has been created.', 'success')
        return redirect(url_for('positions'))
    except sqlite3.IntegrityError:  # Check for same names
        flash(f'{position_name} already exists.', 'danger')
        return redirect(url_for('positions'))

@app.route('/positions/remove/<int:position_id>', methods=['GET'])
@checkadmin
def remove_position(position_id):
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute('SELECT position_name FROM positions WHERE position_id = ?', (position_id,))
    position_name = cur.fetchone()[0]
    cur.execute('DELETE FROM positions WHERE position_id = ?', (position_id,))
    conn.commit()
    conn.close()
    flash(f'{position_name} has been successfully deleted', 'success')
    return redirect(url_for('positions'))

@app.route('/coaches')
@checkadmin
def coaches():
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute("SELECT * FROM coaches")
    coaches = cur.fetchall()
    coaches = coaches[1:]
    conn.close()
    return render_template('coaches.html', coaches=coaches)

@app.route('/coaches/add', methods=['GET', 'POST'])
@checkadmin
def add_coach():
    if request.method == 'POST':
        name = request.form['name']
        contact = request.form['contact']
        try:
            conn = sqlite3.connect(database)
            cur = conn.cursor()
            cur.execute("INSERT INTO coaches (coach_name, coach_contact) VALUES (?,?)", (name, contact))
            conn.commit()
            conn.close()
            return redirect(url_for('coaches'))
        except sqlite3.IntegrityError:
            flash('This contact has already been used', 'danger')
            conn.close()
    return render_template('add_coach.html')

@app.route('/coaches/<int:coach_id>/edit', methods=['GET', 'POST'])
@checkadmin
def edit_coach(coach_id):
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute("SELECT coach_name, coach_contact FROM coaches WHERE coach_id = ?", (coach_id,))
    coach = cur.fetchone()
    conn.close()
    if coach is None:
        return 'Coach not found', 404

    if request.method == 'POST':    # Handle form submission to update the coach
        name = request.form['name']
        contact = request.form['contact']
        try:
            conn = sqlite3.connect(database)
            cur = conn.cursor()
            cur.execute("UPDATE coaches SET coach_name = ?, coach_contact = ? WHERE coach_id = ?" , (name, contact, coach_id))
            conn.commit()
            conn.close()
            return redirect(url_for('coaches'))
        except sqlite3.IntegrityError:
            flash('This contact has already been used', 'danger')
            conn.close()
    coach_name, coach_contact = coach
    return render_template('edit_coach.html', coach_id=coach_id, coach_name=coach_name, coach_contact=coach_contact)

@app.route('/coaches/<int:coach_id>/remove', methods=['GET'])
@checkadmin
def remove_coach(coach_id):
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute("DELETE FROM coaches WHERE coach_id = ?", (coach_id,))
    conn.commit()
    conn.close()
    flash('Coach removed successfully.', 'success')
    return redirect(url_for('coaches'))

@app.route('/players')
@checkadmin
def players():
    conn = sqlite3.connect(database)
    cur = conn.cursor()

    # Retrieve the player and address information
    cur.execute("""
        SELECT 
            players.player_id, 
            players.player_name, 
            players.date_of_birth,
            addresses.address_id,
            addresses.street_address, 
            addresses.city, 
            addresses.state, 
            addresses.zip_code
        FROM players
        JOIN addresses ON players.address_id = addresses.address_id
    """)
    players_data = cur.fetchall()

    # Process the data and create separate lists for players and addresses
    players = []
    addresses = []
    for row in players_data:
        player = {
            'player_id': row[0],
            'player_name': row[1],
            'player_dob': row[2]
        }
        address = {
            'address_id': row[3],
            'street_address': row[4],
            'city': row[5],
            'state': row[6],
            'zip': row[7]
        }
        players.append(player)
        addresses.append(address)

    conn.close()
    return render_template('players.html', players=players, addresses=addresses)

@app.route('/players/add', methods=['GET', 'POST'])
@checkadmin
def add_player():
    if request.method == 'POST':
        name = request.form['name']
        dob = request.form['dob']
        street_address = request.form['street_address']
        city = request.form['city']
        state = request.form['state']
        zip_code = request.form['zip']

        conn = sqlite3.connect(database)
        cur = conn.cursor()

        # Check if the address already exists
        cur.execute("SELECT address_id FROM addresses WHERE street_address = ? AND city = ? AND state = ? AND zip_code = ?", 
                    (street_address, city, state, zip_code))
        existing_address = cur.fetchone()

        if existing_address:
            # Use the existing address
            address_id = existing_address[0]
        else:
            # Insert the new address
            cur.execute("INSERT INTO addresses (street_address, city, state, zip_code) VALUES (?, ?, ?, ?)", 
                        (street_address, city, state, zip_code))
            address_id = cur.lastrowid
            conn.commit()

        # Insert the new player with the address_id
        cur.execute("INSERT INTO players (player_name, date_of_birth, address_id) VALUES (?, ?, ?)", 
                    (name, dob, address_id))
        conn.commit()
        conn.close()

        flash(f'{name} added successfully!', 'success')
        return redirect(url_for('players'))

    return render_template('add_player.html')

@app.route('/players/<int:player_id>/edit', methods=['GET', 'POST'])
@checkadmin
def edit_player(player_id):
    conn = sqlite3.connect(database)
    cur = conn.cursor()

    if request.method == 'POST':
        # Get the updated player and address information from the form
        player_name = request.form['player_name']
        player_dob = request.form['player_dob']
        street_address = request.form['street_address']
        city = request.form['city']
        state = request.form['state']
        zip_code = request.form['zip_code']

        # Check if the address is already in the database
        cur.execute("SELECT address_id FROM addresses WHERE street_address = ? AND city = ? AND state = ? AND zip_code = ?", 
                   (street_address, city, state, zip_code))
        existing_address = cur.fetchone()
        if existing_address:
            # Check if the existing address is used by other players
            new_address_id = existing_address[0]
        else:
            cur.execute("SELECT address_id FROM players WHERE player_id =?", (player_id,))
            address_id = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM players WHERE address_id = ?", (address_id,))
            address_used_count = cur.fetchone()[0]
            if address_used_count > 1:
                cur.execute("INSERT INTO addresses (street_address, city, state, zip_code) VALUES (?, ?, ?, ?)", 
                        (street_address, city, state, zip_code))
                new_address_id = cur.lastrowid
            else:
                cur.execute("UPDATE addresses SET street_address = ?, city = ?, state = ?, zip_code = ? WHERE address_id = ?", 
                           (street_address, city, state, zip_code, address_id))
                new_address_id = address_id

        # Update the player information
        cur.execute("UPDATE players SET player_name = ?, date_of_birth = ?, address_id = ? WHERE player_id = ?", 
                   (player_name, player_dob, new_address_id, player_id))
        conn.commit()

        # Remove unused addresses
        cur.execute("SELECT address_id FROM addresses WHERE address_id NOT IN (SELECT address_id FROM players)")
        unused_addresses = cur.fetchall()
        for address_id, in unused_addresses:
            cur.execute("DELETE FROM addresses WHERE address_id = ?", (address_id,))
        conn.commit()

        conn.close()
        flash(f'{player_name} edited successfully.', 'success')
        return redirect(url_for('players'))

    # Fetch the player and address information for the given player_id
    cur.execute("SELECT players.player_name, players.date_of_birth, addresses.street_address, addresses.city, addresses.state, addresses.zip_code FROM players JOIN addresses ON players.address_id = addresses.address_id WHERE players.player_id = ?", (player_id,))
    player_data = cur.fetchone()
    conn.close()

    if player_data:
        player_name, player_dob, street_address, city, state, zip_code = player_data
        return render_template('edit_player.html', player_id=player_id, player_name=player_name, player_dob=player_dob, street_address=street_address, city=city, state=state, zip_code=zip_code)
    else:
        return redirect(url_for('players'))

@app.route('/players/<int:player_id>/remove', methods=['GET'])
@checkadmin
def remove_player(player_id):
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute("DELETE FROM players WHERE player_id = ?", (player_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('players'))

@app.route('/venues')
@checkadmin
def venues():
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute("SELECT * FROM venues")
    venues = cur.fetchall()
    conn.close()
    return render_template('venues.html', venues=venues)

@app.route('/venues/add', methods=['GET', 'POST'])
@checkadmin
def add_venue():
    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        try:
            conn = sqlite3.connect(database)
            cur = conn.cursor()
            cur.execute("INSERT INTO venues (venue_name, venue_location) VALUES (?,?)", (name, location))
            conn.commit()
            conn.close()
            return redirect(url_for('venues'))
        except sqlite3.IntegrityError:
            flash('This name has already been used', 'danger')
            conn.close()
    return render_template('add_venue.html')

@app.route('/venues/<int:venue_id>/edit', methods=['GET', 'POST'])
@checkadmin
def edit_venue(venue_id):
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute("SELECT venue_name, venue_location FROM venues WHERE venue_id = ?", (venue_id,))
    venue = cur.fetchone()
    conn.close()
    if venue is None:
        return 'Venue not found', 404

    if request.method == 'POST':
        # Handle form submission to update the coach
        name = request.form['name']
        location = request.form['location']
        try:
            conn = sqlite3.connect(database)
            cur = conn.cursor()
            cur.execute("UPDATE venues SET venue_name = ?, venue_location = ? WHERE venue_id = ?" , (name, location, venue_id))
            conn.commit()
            conn.close()
            flash('Venue updated successfully.', 'success')
            return redirect(url_for('venues'))
        except sqlite3.IntegrityError:
            flash('This name has already been used', 'danger')
            conn.close()
    venue_name, venue_location = venue
    return render_template('edit_venue.html', venue_id=venue_id, venue_name=venue_name, venue_location=venue_location)

@app.route('/venues/<int:venue_id>/remove', methods=['GET'])
@checkadmin
def remove_venue(venue_id):
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM tournaments WHERE venue_id = ?", (venue_id,))
    count = cur.fetchone()[0]
    if count:
        flash('This venue is being/has been used already.', 'danger')
    else:
        cur.execute("DELETE FROM venues WHERE venue_id = ?", (venue_id,))
        conn.commit()
        flash('Venue removed successfully.', 'success')
    conn.close()
    return redirect(url_for('venues'))

@app.route('/tournaments', methods=['GET', 'POST'])
@checkadmin
def tournaments():
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute('SELECT * FROM tournaments')
    tournaments = cur.fetchall()
    conn.close()
    return render_template('tournaments.html', tournaments=tournaments)

@app.route('/tournaments/add', methods=['POST'])
@checkadmin
def add_tournament():
    tournament_name = request.form['tournament_name']
    try:
        conn = sqlite3.connect(database)
        cur = conn.cursor()
        cur.execute('INSERT INTO tournaments (tournament_name) VALUES (?)', (tournament_name,))
        conn.commit()
        conn.close()
        flash(f'Tournament {tournament_name} has been created.', 'success')
        return redirect(url_for('tournaments'))
    except sqlite3.IntegrityError:
        flash(f'{tournament_name} already exists.', 'danger')
        return redirect(url_for('tournaments'))

@app.route('/tournaments/remove/<int:tournament_id>', methods=['GET'])
@checkadmin
def remove_tournament(tournament_id):
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) AS inuse FROM matches WHERE tounament_id = ? ', (tournament_id,))
    inuse = cur.fetchone()[0]
    cur.execute('SELECT tournament_name FROM tournaments WHERE tournament_id = ?', (tournament_id,))
    tournament_name = cur.fetchone()[0]
    if inuse:
        conn.close()
        flash(f'{tournament_name} is currently in use.', 'danger')
        return redirect(url_for('tournaments'))
    cur.execute('DELETE FROM tournaments WHERE tournament_id = ?', (tournament_id,))
    conn.commit()
    conn.close()
    flash(f'{tournament_name} has been successfully deleted', 'success')
    return redirect(url_for('tournaments'))

@app.route('/club/<int:club_id>')
@checklogin
def club(club_id):
    if club_id != session['user_id']:
        flash('You are not permitted to access this page.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        with sqlite3.connect(database) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Retrieve club information from the database
            cur.execute("SELECT * FROM clubs WHERE club_id = ?", (session['user_id'],))
            club_data = cur.fetchone()

            if club_data:
                return render_template('club.html', club_data=club_data)
            else:
                flash('No club information found.', 'danger')
                return redirect(url_for('dashboard'))

    except sqlite3.Error as e:
        flash(f'Database error: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))
    
@app.route('/edit_club_contact/<int:club_id>', methods=['GET', 'POST'])
@checklogin
def edit_club_contact(club_id):
    if club_id != session['user_id']:
        flash('You are not permitted to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    try:
        with sqlite3.connect(database) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            if request.method == 'POST':
                club_contact = request.form['club_contact']

                # Update the club contact phone in the database
                cur.execute("UPDATE clubs SET club_contact = ? WHERE club_id = ?", (club_contact, club_id))
                conn.commit()

                flash('Club contact phone updated successfully.', 'success')
                return redirect(url_for('club', club_id=club_id))

            # Retrieve the current club information from the database
            cur.execute("SELECT * FROM clubs WHERE club_id = ?", (club_id,))
            club_data = cur.fetchone()

            if club_data:
                return render_template('edit_club_contact.html', club_data=club_data)
            else:
                flash('No club information found.', 'danger')
                return redirect(url_for('dashboard'))

    except sqlite3.Error as e:
        flash(f'Database error: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/teams/<int:club_id>', methods=['GET'])
@checklogin
def teams(club_id):
    if club_id != session['user_id']:
        flash('You are not permitted to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    # Fetch the teams for the club from the database
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute("SELECT team_id, team_name FROM teams WHERE club_id = ?", (club_id,))
    teams = cur.fetchall()
    conn.close
    return render_template('teams.html', club_id=club_id, teams=teams)

@app.route('/teams/<int:club_id>/create', methods=['GET', 'POST'])
@checklogin
def create_team(club_id):
    if club_id != session['user_id']:
        flash('You are not permitted to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        try:
            team_name = request.form['team_name']
            division_id = request.form['division']
            conn = sqlite3.connect(database)
            cur = conn.cursor()
            cur.execute("INSERT INTO teams (team_name, club_id, division_id) VALUES (?,?,?)", (team_name, club_id, division_id))
            conn.commit()
            conn.close()
            flash('Team has been created successfully', 'success')
            return redirect(url_for('teams', club_id=club_id))
        except sqlite3.IntegrityError:
            flash('This team already exists, try another name.', 'danger')
            
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute("SELECT * FROM divisions")
    divisions = cur.fetchall()
    conn.close()
    return render_template('create_team.html', club_id=club_id, divisions=divisions)

@app.route('/teams/<int:club_id>/<int:team_id>')
@checklogin
def team_details(club_id, team_id):
    if club_id != session['user_id']:
        flash('You are not permitted to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    # Fetch the team details from the SQLite database
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute("SELECT team_name, division_id, coach_id FROM teams WHERE team_id = ?", (team_id,))
    team_data = cur.fetchone()
    team_name, division_id, coach_id = team_data
    cur.execute("SELECT division_name FROM divisions WHERE division_id = ?", (division_id,))
    division = cur.fetchone()
    if not division:
        cur.execute("UPDATE teams SET division_id = 0 WHERE team_id = ?", (team_id,))
        conn.commit()
        division_name = 'N/A'
    else:
        division_name = division[0]
    if coach_id:
        cur.execute("SELECT coach_name, coach_contact FROM coaches WHERE coach_id = ?", (coach_id,))
        coach_data = cur.fetchone()
        coach_name = coach_data[0]
        coach_contact = coach_data[1]
    else:
        coach_name = coach_contact = 'N/A'
    cur.execute("""SELECT p.player_id, p.player_name, p.date_of_birth,
                a.street_address, a.city, a.state, a.zip_code 
                FROM players p 
                JOIN addresses a ON p.address_id = a.address_id 
                WHERE team_id = ?""", (team_id,))
    players = cur.fetchall()
    conn.close()
    print(players)

    return render_template('team_details.html', 
                           club_id=club_id, 
                           team_id=team_id, 
                           team_name=team_name, 
                           division_name=division_name, 
                           coach_name=coach_name, 
                           coach_contact=coach_contact,
                           players=players)
    
@app.route('/teams/<int:club_id>/<int:team_id>/addplayer', methods=['GET', 'POST'])  
@checklogin
def team_add_player(club_id, team_id):
    if club_id != session['user_id']:
        flash('You are not permitted to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        player = request.form['player']
        conn = sqlite3.Connection(database)
        cur = conn.cursor()
        cur.execute("UPDATE players SET team_id = ? WHERE player_id = ?",
                    (team_id, player))
        conn.commit()
        conn.close()
        return redirect(url_for('team_details', club_id=club_id, team_id=team_id))
    conn = sqlite3.Connection(database) 
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS inteam FROM players WHERE team_id = ?", (team_id,))
    inteam = cur.fetchone()[0]
    if inteam >= 10:
        flash('The team already has 10 players.', 'danger')
        return redirect(url_for('team_details', club_id=club_id, team_id=team_id))
    cur.execute("SELECT player_id, player_name FROM players WHERE team_id IS NULL")
    players = cur.fetchall()
    conn.close()
    return render_template('team_add_player.html', club_id=club_id, team_id=team_id, players=players)
    
@app.route('/teams/<int:club_id>/<int:team_id>/<int:player_id>/remove', methods=['GET'])  
@checklogin
def team_remove_player(club_id, team_id, player_id):
    if club_id != session['user_id']:
        flash('You are not permitted to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    conn = sqlite3.Connection(database)
    cur = conn.cursor()
    cur.execute("UPDATE players SET team_id = NULL, position_id = NULL WHERE player_id = ?", (player_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('team_details', club_id=club_id, team_id=team_id))
    
@app.route('/teams/<int:club_id>/<int:team_id>/edit', methods=['GET', 'POST'])
@checklogin
def edit_team(club_id, team_id):
    if club_id != session['user_id']:
        flash('You are not permitted to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        # Handle form submission
        team_name = request.form['team_name']
        coach_id = request.form['coach_id']
        division_id = request.form['division_id']
        conn = sqlite3.connect(database)
        cur = conn.cursor()
        try:
            cur.execute("UPDATE teams SET team_name = ?, coach_id = ?, division_id = ? WHERE team_id = ?", (team_name, coach_id, division_id, team_id))
            conn.commit()
            conn.close()
            return redirect(url_for('team_details', team_id=team_id, club_id=club_id))
        except sqlite3.IntegrityError:
            flash('This team name is already taken, choose another one', 'danger')
            conn.close()
        # Update the team information in the database

    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute("SELECT team_name, division_id, coach_id FROM teams WHERE team_id = ?", (team_id,))
    team_data = cur.fetchone()
    team = {}
    team['team_name'] = team_data[0]
    team['division_id'] = team_data[1]
    team['coach_id'] = team_data[2]
    team['team_id'] = team_id
    cur.execute("SELECT * FROM divisions")
    divisions = cur.fetchall()
    cur.execute("SELECT * FROM coaches")
    coaches = cur.fetchall()
    conn.close()
    return render_template('edit_team.html', team=team, divisions=divisions, coaches=coaches, club_id=club_id)

@app.route('/teams/<int:club_id>/<int:team_id>/delete', methods=['GET']) 
@checklogin
def delete_team(club_id, team_id):
    if club_id != session['user_id']:
        flash('You are not permitted to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute("DELETE FROM teams WHERE team_id = ?", (team_id,))
    conn.commit()
    conn.close()
    flash('Team has been deleted successfully', 'success')
    return redirect(url_for('teams', club_id=club_id))

@app.route('/view_tournaments', methods=['GET'])
@checklogin
def view_tournaments():
    conn = sqlite3.Connection(database)
    cur = conn.cursor()
    cur.execute("SELECT * FROM tournaments")
    tournaments = cur.fetchall()
    conn.close()
    return render_template('view_tounaments.html', tournaments=tournaments)

@app.route('/view_tournaments/<int:tournament_id>', methods=['GET'])
@checklogin
def view_matches(tournament_id):
    conn = sqlite3.Connection(database)
    cur = conn.cursor()
    cur.execute("""SELECT
                        v.venue_name,
                        m.match_date,
                        m.match_time,
                        ht.team_name AS home_team,
                        m.home_team_score,
                        m.away_team_score,
                        at.team_name AS away_team,
                        m.match_id
                    FROM
                        matches m
                        JOIN venues v ON m.venue_id = v.venue_id
                        JOIN teams ht ON m.home_team_id = ht.team_id
                        JOIN teams at ON m.away_team_id = at.team_id
                    WHERE m.tournament_id = ?""", (tournament_id,))
    matches = cur.fetchall()
    cur.execute("SELECT tournament_name FROM tournaments WHERE tournament_id = ?", (tournament_id,))
    tournament_name = cur.fetchone()[0]
    return render_template('view_matches.html', matches=matches, tournament_id=tournament_id, tournament_name=tournament_name)
    
@app.route('/tournaments/<int:tournament_id>/add', methods=['GET','POST'])
def add_match(tournament_id):
    if request.method == 'POST':
        venue = request.form['venue']
        date = request.form['date']
        time = request.form['time']
        home_team = request.form['home_team']
        home_team_score = int(request.form['home_team_score'])
        away_team_score = int(request.form['away_team_score'])
        away_team = request.form['away_team']
        conn = sqlite3.Connection(database)
        cur = conn.cursor()
        cur.execute("""INSERT INTO matches (venue_id, match_date, match_time, home_team_id, home_team_score, 
                    away_team_score, away_team_id, tournament_id) VALUES (?,?,?,?,?,?,?,?)""",
                    (venue, date, time, home_team, home_team_score, away_team_score, away_team, tournament_id))
        conn.commit()
        conn.close()
        flash('Match added successfully', 'success')
        return redirect(url_for('view_matches', tournament_id=tournament_id ))

    conn = sqlite3.Connection(database)
    cur = conn.cursor()
    cur.execute("""SELECT t.team_id, t.team_name
                    FROM teams t
                    INNER JOIN players p ON t.team_id = p.team_id
                    GROUP BY t.team_id, t.team_name
                    HAVING COUNT(p.player_id) > 0;""")
    teams = cur.fetchall()
    cur.execute("SELECT * FROM venues")
    venues = cur.fetchall()
    conn.close()
    return render_template('add_match.html', tournament_id=tournament_id, teams=teams, venues=venues)

@app.route('/view_tournaments/<int:tournament_id>/<int:match_id>')
@checklogin
def match_stats(tournament_id, match_id):
    conn = sqlite3.Connection(database)
    cur = conn.cursor()
    cur.execute("""SELECT 
                        p1.position_name,
                        p2.position_name,
                        players.player_name,
                        pms.points_scored
                    FROM 
                        player_match_stats pms
                    JOIN 
                        matches ON pms.match_id = matches.match_id
                    JOIN 
                        players ON pms.player_id = players.player_id
                    JOIN 
                        positions p1 ON pms.position_1_id = p1.position_id
                    JOIN 
                        positions p2 ON pms.position_2_id = p2.position_id
                    WHERE 
                        matches.match_id = ?
                    AND matches.home_team_id = players.team_id""", (match_id,))
    home_team = cur.fetchall()
    cur.execute("""SELECT 
                        p1.position_name,
                        p2.position_name,
                        players.player_name,
                        pms.points_scored
                    FROM 
                        player_match_stats pms
                    JOIN 
                        matches ON pms.match_id = matches.match_id
                    JOIN 
                        players ON pms.player_id = players.player_id
                    JOIN 
                        positions p1 ON pms.position_1_id = p1.position_id
                    JOIN 
                        positions p2 ON pms.position_2_id = p2.position_id
                    WHERE 
                        matches.match_id = ?
                    AND matches.away_team_id = players.team_id""", (match_id,))
    away_team = cur.fetchall()
    cur.execute("SELECT home_team_score, away_team_score FROM matches WHERE match_id = ?", (match_id,))
    home_team_score, away_team_score = cur.fetchone()
    conn.close()
    return render_template('match_stats.html', home_team=home_team, away_team=away_team, home_team_score=home_team_score, 
                           away_team_score=away_team_score, tournament_id=tournament_id, match_id=match_id)
    
@app.route('/view_tournaments/<int:tournament_id>/<int:match_id>/<team>', methods=['GET', 'POST'])
@checklogin
def edit_match_stats(tournament_id, match_id, team):
    if request.method == 'POST':
        player_ids = request.form.getlist('player_ids[]')
        player_positions1 = request.form.getlist('player_positions1[]')
        player_positions2 = request.form.getlist('player_positions2[]')
        player_scores = request.form.getlist('player_scores[]')

        # Convert scores to integers
        player_scores = list(map(int, player_scores))
        player_data = []
        for i in range(len(player_ids)):
            tempdict = {'match_id': match_id,
                        'player_id': player_ids[i],
                        'points_scored': player_scores[i],
                        'position_1_id': player_positions1[i],
                        'position_2_id': player_positions2[i]}
            player_data.append(tempdict)
            
        conn = sqlite3.Connection(database)
        cur = conn.cursor()
        for player in player_data:
            cur.execute("""INSERT INTO player_match_stats (match_id, player_id, points_scored, position_1_id, position_2_id)
                        VALUES (:match_id, :player_id, :points_scored, :position_1_id, :position_2_id)
                        ON CONFLICT(match_id, player_id) DO UPDATE SET
                            points_scored = excluded.points_scored,
                            position_1_id = excluded.position_1_id,
                            position_2_id = excluded.position_2_id""", player)
        conn.commit()
        conn.close()
        flash('Stats edited successfully', 'success')
        return redirect(url_for('match_stats', tournament_id=tournament_id, match_id=match_id))
            
    conn = sqlite3.Connection(database)
    cur = conn.cursor()
    cur.execute(f"SELECT {team}_team_id FROM matches WHERE match_id = ?", (match_id,))
    team_id = cur.fetchone()[0]

    # Fetch players with stats if available, or default values if not
    cur.execute("""
        SELECT p.player_id, p.player_name, 
               COALESCE(pms.position_1_id, '') AS position_1_id, 
               COALESCE(pms.position_2_id, '') AS position_2_id, 
               COALESCE(pms.points_scored, 0) AS points_scored
        FROM players p
        LEFT JOIN player_match_stats pms ON p.player_id = pms.player_id AND pms.match_id = ?
        WHERE p.team_id = ?
    """, (match_id, team_id))
    players = cur.fetchall()

    cur.execute("SELECT * FROM positions")
    positions = cur.fetchall()
    cur.execute(f"SELECT {team}_team_score FROM matches WHERE match_id = ?", (match_id,))
    total_score = cur.fetchone()[0]
    conn.close()
    return render_template('edit_match_stats.html', 
                           tournament_id=tournament_id,
                           players=players, 
                           positions=positions, 
                           match_id=match_id, 
                           team=team, 
                           total_score=total_score)
    
@app.route('/player_stats')
@checklogin
def player_stats():
    conn = sqlite3.Connection(database)
    cur = conn.cursor()
    cur.execute("""SELECT p.player_id, p.player_name, p.date_of_birth, c.club_name,t.team_name, d.division_name
                FROM players p 
                    JOIN teams t ON p.team_id = t.team_id
                    JOIN clubs c ON t.club_id = c.club_id
                    JOIN divisions d ON t.division_id = d.division_id
                    ORDER BY p.player_name""")
    players = cur.fetchall()

    return render_template('view_players.html', players=players)

@app.route('/player_stats/<int:player_id>')
@checklogin
def player_matches(player_id):
    conn = sqlite3.connect(database)  # Ensure you replace 'database.db' with your actual database name
    cur = conn.cursor()

    # Fetch match data for the player
    cur.execute("""SELECT m.match_date, m.home_team_id, m.away_team_id, 
                   m.home_team_score, m.away_team_score, pms.points_scored, p.team_id
                   FROM player_match_stats pms 
                   JOIN matches m ON pms.match_id = m.match_id
                   JOIN players p ON pms.player_id = p.player_id
                   WHERE pms.player_id = ?""", (player_id,))
    matches_data = cur.fetchall()

    # Fetch the player's team id
    cur.execute("SELECT team_id FROM players WHERE player_id = ?", (player_id,))
    team_id = cur.fetchone()[0]

    # Determine the team score for each match
    matches = []
    oppteam_id = 0
    for match in matches_data:
        if match[1] == team_id:
            team_score = match[3]
            oppteam_id = match[2]
        else:
            team_score = match[4]
            oppteam_id = match[1]

        # Calculate the percentage safely
        if team_score != 0:
            percentage = round(match[5] * 10000 / team_score) / 100
        else:
            percentage = 0  # Or handle as appropriate (e.g., "N/A", "0%")

        # Fetch the team name
        cur.execute("SELECT team_name FROM teams WHERE team_id = ?", (oppteam_id,))
        team_name = cur.fetchone()[0]

        # Append match details
        matches.append((match[0], team_name, match[5], percentage))

    # Fetch the player's name
    cur.execute("SELECT player_name FROM players WHERE player_id = ?", (player_id,))
    player_name = cur.fetchone()[0]

    conn.close()
    return render_template('view_player_matches.html', player_name=player_name, matches=matches)

@app.route('/logout')
@checklogin
def logout():
    session.clear()
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.before_request
def remove_extra_slash():
    # Get the current request path
    path = request.path
    # Check if the path ends with a '/'
    if path != '/' and path.endswith('/'):
        # Construct the corrected URL
        corrected_path = path[:-1]
        return redirect(corrected_path)
    else:
        return None

if __name__ == '__main__':
    database = os.getenv('DATABASE_NAME')
    if database is None:
        print('No database name provided.')
        exit(1)
        
    if not os.path.isfile(os.path.abspath(f'./{database}')):
        print('This database does not exist.')
        exit(2)
        
    app.run(debug=True)
