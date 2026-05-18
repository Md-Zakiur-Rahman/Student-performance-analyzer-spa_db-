# Student Performance Analyzer

A desktop application for managing student performance records with role-based access for administrators, faculty, and students. The app is built with Python, PyQt6, and MySQL, and uses a modular controller/service structure with Qt Designer UI files.

## Highlights

- Role-based dashboards for Admin, Faculty, and Student users.
- Automatic database setup from `PRN_setup.sql` when the database is missing.
- Login by username or student PRN.
- Admin user management for students, faculty, and admins.
- Faculty subject assignment with a multi-select subject picker.
- Faculty mark entry by assigned subject: select one subject, view all students, edit marks per student, then save.
- Analytics dashboard with summary stats, grade distribution, department stats, department leaderboard, subject grades, and pass/fail status.
- CSV exports for student reports and high performers.
- Audit logging for important administrative and academic actions.

## Tech Stack

- Python 3.14
- PyQt6
- MySQL
- mysql-connector-python
- PyInstaller
- Qt Designer `.ui` files
- QSS stylesheet

## Project Structure

```text
spa_db/
├── main.py                     # Application entry point
├── db.py                       # Database connection, setup, authentication, audit helpers
├── academic.py                 # Shared academic reports and student/marks operations
├── admin.py                    # Admin service operations
├── faculty.py                  # Faculty service operations
├── std.py                      # Student service operations
├── PRN_setup.sql               # Database schema and startup SQL
├── PRN_queries.txt             # Query reference
├── PRN_spa.spec                # PyInstaller build specification
├── requirements.txt
├── controllers/
│   ├── login_controller.py
│   ├── admin_controller.py
│   ├── faculty_controller.py
│   └── student_controller.py
└── ui/
    ├── login.ui
    ├── admin.ui
    ├── faculty.ui
    ├── student.ui
    └── cyberpunk.qss
```

## Running From Source

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the app:

```powershell
python main.py
```

The login screen only asks for application credentials. MySQL setup credentials are handled during startup with `SPA_DB_PASSWORD` or a one-time setup dialog if the database needs to be created.

## Running The Executable

Use the root executable:

```powershell
.\PRN_spa.exe
```

Fresh PyInstaller builds are generated in:

```text
dist\PRN_spa.exe
```

## Database Setup

The app automatically checks whether `spa_db` exists. If it is missing, it runs `PRN_setup.sql` to create the database, tables, constraints, views, and MySQL application users.

For unattended setup, set the root password before launching:

```powershell
setx SPA_DB_PASSWORD "your_mysql_root_password"
```

Manual setup is also supported:

```sql
SOURCE D:/spa_db/PRN_setup.sql;
```

The setup script creates only the default admin account. It does not seed sample subjects, students, faculty, or marks.

Default admin:

```text
username: admin
password: adminpass
```

## Role Capabilities

### Admin

- Manage users: create, edit, activate/deactivate, and delete users.
- Manage subjects: add, edit, and delete subjects.
- Create student users with linked student profiles.
- Create faculty users and assign subjects using a selector.
- View and search students by department.
- View analytics, top performers, department leaderboard, and audit log.
- Add bonus marks by department, capped at 100.
- Export high performers above the overall average to a timestamped CSV.
- Create MySQL application users.

### Faculty

- View assigned subjects.
- Search students by PRN.
- Enter marks for one selected subject across all students.
- Save subject marks from an editable roster table.
- View students, analytics, leaderboard, and department reports.
- Add bonus marks by department, capped at 100.
- Export high performers to timestamped CSV.

### Student

- View own subject-wise marks.
- View GPA/average.
- View analytics and leaderboard.
- Export own marks report to CSV.

## Analytics

The analytics dashboard includes:

- Total students, average marks, highest marks, and lowest marks.
- Grade distribution using `CASE` inside `SUM()`:
  - A: `>= 90`
  - B: `75-89`
  - C: `60-74`
  - D: `40-59`
  - F: `< 40`
- Department-wise average, highest, and lowest marks using `GROUP BY`.
- Top 3 performers using `ORDER BY ... LIMIT 3`.
- Department leaderboard ranked by average marks.
- Subject-wise grade and pass/fail status.
- Marks distribution report by grade band.

## Building The Executable

Rebuild the Windows executable with:

```powershell
python -m PyInstaller --clean --noconfirm PRN_spa.spec
```

Then copy the generated executable if needed:

```powershell
Copy-Item .\dist\PRN_spa.exe .\PRN_spa.exe -Force
```

The spec file bundles `PRN_setup.sql` and the `ui/` folder, excludes the optional native MySQL extension, and builds a windowed app without a console.

## Notes

- The app does not activate or run `.venv` automatically.
- `build/`, `dist/`, `.venv/`, and `__pycache__/` are local generated folders.
- Keep `PRN_setup.sql` with the project because the executable uses it for first-run database setup.

## Developer Notes (recent)

- Date: 2026-05-18
- Resolved a corrupted UI file issue in `ui/admin.ui` that caused an XML parse error on startup. The file was replaced with a well-formed Qt Designer `.ui` and missing widgets expected by `AdminController` were restored (e.g. `addSubjectButton`, `createUserButton`, `toggleUserButton`, `commandInput`, `executeButton`, `auditTable`).
- Verification: `python main.py` was run locally and no UI parse exception occurred; the Admin controller initializes without the earlier crash.
- If you hit UI-related errors, check `ui/admin.ui` and ensure widget names match those referenced in `controllers/admin_controller.py`.

