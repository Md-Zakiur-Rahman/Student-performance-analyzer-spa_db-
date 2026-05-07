# Student Performance Analyzer

Student Performance Analyzer is a desktop application for managing and viewing academic performance data. It is built with Python, PyQt6, and MySQL, with a cyberpunk-inspired dark neon interface.

The application supports role-based access for Admin, Faculty, and Student users. It includes login by username or PRN, student and subject management, faculty subject restrictions, subject-wise marks, GPA calculation, CSV export, and audit logging.

## Tech Stack

- Python 3.14
- PyQt6
- MySQL
- Qt Designer `.ui` files
- QSS stylesheet
- MVC-style controller structure

## Project Structure

```text
spa_db/
├── main.py
├── db.py
├── admin.py
├── faculty.py
├── std.py
├── README.md
│
├── controllers/
│   ├── login_controller.py
│   ├── admin_controller.py
│   ├── faculty_controller.py
│   ├── student_controller.py
│   └── __init__.py
│
├── ui/
│   ├── login.ui
│   ├── admin.ui
│   ├── faculty.ui
│   ├── student.ui
│   └── cyberpunk.qss
│
├── PRN_analyzer.py
├── PRN_setup.sql
├── PRN_queries.txt
└── PRN_spa.exe
```

## Running The App

Run the modular PyQt6 application from source:

```powershell
python main.py
```

Or run the Windows executable:

```powershell
.\PRN_spa.exe
```

The executable is located at the project root: `PRN_spa.exe`.

Login accepts either username or PRN. The MySQL password is entered on the login screen so the app can connect to the local database.

## Database Setup

Run `PRN_setup.sql` in MySQL to create the database, tables, constraints, sample data, views, and role-based MySQL users.

Example:

```sql
SOURCE D:/spa_db/PRN_setup.sql;
```

The setup script creates these base tables:

- `users`
- `students`
- `subjects`
- `student_marks`
- `faculty_subjects`
- `audit_log`

It also creates these views:

- `v_analytics_summary`
- `v_audit_recent`
- `v_student_portal`

## Executable Behavior

- `PRN_spa.exe` (and running `python main.py`) will attempt to ensure the database and tables exist on startup by executing `PRN_setup.sql` automatically.
- The startup routine uses the `SPA_DB_PASSWORD` environment variable for the MySQL root password if set. If `SPA_DB_PASSWORD` is not set the app will prompt for the MySQL root password (note: a console prompt appears when running from source).
- For headless or installer scenarios, set the password first:

```powershell
setx SPA_DB_PASSWORD "your_mysql_root_password"
```

- If automatic setup isn't possible, you can run the SQL manually:

```sql
SOURCE D:/spa_db/PRN_setup.sql;
```

## Project Files

- `main.py` starts the modular PyQt6 desktop app.
- `db.py` handles database connection, password hashing, login authentication, and audit logging.
- `admin.py`, `faculty.py`, and `std.py` contain role-specific backend logic.
- `controllers/` connects the UI screens to backend logic.
- `ui/` contains Qt Designer layouts and the cyberpunk QSS theme.
- `PRN_analyzer.py` is a standalone single-file version of the application.
- `PRN_queries.txt` lists the SQL queries used by the project with short explanations.
- `PRN_spa.exe` is the Windows executable build.

## Roles

Admin:
- View users, subjects, and audit log
- Create users
- Add subjects
- Toggle user active/disabled status
- Creating a `student` user also creates the linked row in `students` with name, department, and PRN.
- Creating a `faculty` user assigns selected subjects through `faculty_subjects`.

Faculty:
- View assigned subjects
- Search students by PRN
- Update individual marks
- View subject-wise student roster
- Bulk update marks for assigned subjects
- Faculty dashboards only load subjects assigned to that faculty account, so marks updates are restricted by `faculty_subjects`.

Student:
- View subject-wise marks
- View GPA
- Export marks report as CSV

## Notes

- Keep `PRN_setup.sql` with the project because it reproduces the database schema on another machine.
- `__pycache__` folders are generated automatically by Python and are ignored.
- `PRN_spa.exe` may require MySQL client libraries on another Windows machine.

### Executable DB setup behavior

- When you run the windowed executable `PRN_spa.exe`, the application will prompt with a GUI password dialog to obtain the MySQL root password and then run `PRN_setup.sql` to create the database and tables if needed.
- If you build a console exe or run from source, the app will use the `SPA_DB_PASSWORD` environment variable or fall back to a console prompt.
- Rebuild the executable after source changes so the new startup behavior is included (example using PyInstaller):

```powershell
pyinstaller --onefile --add-data "PRN_setup.sql;." --name PRN_spa main.py
```
