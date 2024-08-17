# Sports Management Program

## Usage

### Create a New Database
To create a new database with the desired name, run:

```bash
python writedb.py {database}.db
```

**Example:**

```bash
python writedb.py maindatabase.db
```

This command creates a database named `maindatabase.db` and populates it with the schema.

### Generate and Import Random Data
To generate random data and populate the database, use:

```bash
python importrandomdata.py {database}.db {num_players} {num_teams} {num_clubs} {output}.txt
```

**Example:**

```bash
python importrandomdata.py maindatabase.db 1000 100 10 accounts.txt
```

This command will:
- Fill `maindatabase.db` with 1000 players, 100 teams, and 10 clubs.
- Output the generated account names and passwords to `accounts.txt`.

**Note:** This will wipe the existing data in the database.

### Run the Application
To run the application with the target database, use:

```bash
python run.py {database}.db
```

**Example:**

```bash
python run.py maindatabase.db
```

This command runs the application with the specified database. Ensure the database exists before running the application, as it will exit if the database is not found.

## Notes
- The program features two panels: Admin and Dashboard.
- The default admin account credentials are:
  - **Username:** admin
  - **Password:** admin

---
