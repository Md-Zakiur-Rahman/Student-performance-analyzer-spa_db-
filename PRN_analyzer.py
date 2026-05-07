import csv
import hashlib
import sys
from pathlib import Path

import mysql.connector
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "spa_db",
}


QSS = """
* { color: #00FF66; font-family: Consolas, "Courier New", monospace; font-size: 13px; }
QMainWindow, QWidget { background: #020702; }
QFrame { background: #041404; border: 2px solid #00FF66; }
QLineEdit, QComboBox, QTextEdit, QTableWidget, QListWidget {
    background: #020702; border: 1px solid #00FF66;
    selection-background-color: #00FF66; selection-color: #020702;
}
QPushButton { background: #041404; border: 1px solid #00FF66; padding: 8px 14px; font-weight: 700; }
QPushButton:hover, QTabBar::tab:selected { background: #00FF66; color: #020702; }
QTabWidget::pane { border: 2px solid #00FF66; background: #041404; }
QTabBar::tab { background: #041404; border: 1px solid #00FF66; padding: 8px 22px; min-width: 90px; }
QHeaderView::section { background: #041404; border: 1px solid #00FF66; padding: 6px; font-weight: 700; }
"""


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def log_audit(user_id, action: str, details: str = "") -> None:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO audit_log(user_id, action, details) VALUES (%s, %s, %s)", (user_id, action, details))
        conn.commit()
        conn.close()
    except Exception:
        pass


def authenticate(identifier: str, password: str, mysql_password: str) -> dict | None:
    DB_CONFIG["password"] = mysql_password
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM users WHERE username=%s AND password_hash=%s AND is_active=TRUE",
            (identifier, hash_password(password)),
        )
        user = cur.fetchone()
        if not user:
            cur.execute(
                """
                SELECT u.*
                FROM users u
                JOIN students s ON s.user_id = u.id
                WHERE s.prn=%s AND u.password_hash=%s AND u.is_active=TRUE
                """,
                (identifier, hash_password(password)),
            )
            user = cur.fetchone()

        if not user:
            log_audit(None, "LOGIN_FAILED", f"identifier={identifier}")
            return None

        cur.execute("SELECT id FROM students WHERE user_id=%s", (user["id"],))
        student = cur.fetchone()
        user["student_id"] = student["id"] if student else None
        log_audit(user["id"], "LOGIN_SUCCESS", f"identifier={identifier} role={user['role']}")
        return user
    finally:
        conn.close()


def fetch_all(query: str, params=()):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        return cur.fetchall()
    finally:
        conn.close()


def execute(query: str, params=()) -> int:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        return cur.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def subjects() -> list[str]:
    return [row[0] for row in fetch_all("SELECT name FROM subjects ORDER BY name")]


class BaseWindow(QMainWindow):
    def panel(self):
        frame = QFrame()
        layout = QVBoxLayout(frame)
        return frame, layout

    def log(self, text: str) -> None:
        self.terminal.append(f"> {text}")


class LoginWindow(BaseWindow):
    def __init__(self):
        super().__init__()
        self.dashboard = None
        self.setWindowTitle("SPA LOGIN NODE")
        root = QWidget()
        layout = QHBoxLayout(root)
        self.setCentralWidget(root)

        left, left_layout = self.panel()
        left_layout.addWidget(QLabel("STUDENT PERFORMANCE ANALYZER"))
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setPlainText("BOOT SEQUENCE: READY\nAUTH CHANNEL: USERNAME OR PRN")
        left_layout.addWidget(self.terminal)

        right, right_layout = self.panel()
        right_layout.addWidget(QLabel("ACCESS TERMINAL"))
        self.identifier = QLineEdit()
        self.identifier.setPlaceholderText("USERNAME / PRN")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("PASSWORD")
        self.mysql_password = QLineEdit()
        self.mysql_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.mysql_password.setPlaceholderText("MYSQL ROOT PASSWORD")
        login_btn = QPushButton("LOGIN")
        login_btn.clicked.connect(self.login)
        right_layout.addWidget(self.identifier)
        right_layout.addWidget(self.password)
        right_layout.addWidget(self.mysql_password)
        right_layout.addWidget(login_btn)
        right_layout.addStretch()
        right_layout.addWidget(QLabel("STATUS: LOCKED"))

        layout.addWidget(left, 2)
        layout.addWidget(right, 1)
        self.resize(980, 620)

    def login(self) -> None:
        try:
            user = authenticate(self.identifier.text().strip(), self.password.text(), self.mysql_password.text())
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", str(exc))
            return

        if not user:
            QMessageBox.warning(self, "Login Failed", "Invalid credentials or inactive account.")
            self.log("ACCESS DENIED")
            return

        role = user["role"]
        if role == "admin":
            self.dashboard = AdminWindow(user, self.return_to_login)
        elif role == "faculty":
            self.dashboard = FacultyWindow(user, self.return_to_login)
        elif role == "student":
            self.dashboard = StudentWindow(user, self.return_to_login)
        else:
            QMessageBox.critical(self, "Access Denied", f"Unknown role: {role}")
            return

        self.dashboard.show()
        self.hide()

    def return_to_login(self) -> None:
        self.identifier.clear()
        self.password.clear()
        self.terminal.setPlainText("SESSION ENDED\nAUTH CHANNEL READY")
        self.show()


class AdminWindow(BaseWindow):
    def __init__(self, user: dict, on_logout):
        super().__init__()
        self.user = user
        self.on_logout = on_logout
        self.setWindowTitle("SPA ADMIN DASHBOARD")
        root = QWidget()
        outer = QVBoxLayout(root)
        self.setCentralWidget(root)

        header = QHBoxLayout()
        header.addWidget(QLabel("ADMIN CONTROL PANEL"))
        header.addStretch()
        refresh = QPushButton("REFRESH")
        refresh.clicked.connect(self.refresh)
        logout = QPushButton("LOGOUT")
        logout.clicked.connect(self.logout)
        header.addWidget(refresh)
        header.addWidget(logout)
        outer.addLayout(header)

        body = QHBoxLayout()
        self.tabs = QTabWidget()
        self.users_table = QTableWidget()
        self.audit_table = QTableWidget()
        self.subject_list = QListWidget()
        self.tabs.addTab(self.users_table, "USERS")
        self.tabs.addTab(self.subject_list, "SUBJECTS")
        self.tabs.addTab(self.audit_table, "AUDIT")
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        left, left_layout = self.panel()
        left_layout.addWidget(self.tabs)
        left_layout.addWidget(self.terminal)

        right, right_layout = self.panel()
        right_layout.addWidget(QLabel(f"USERNAME: {user['username']}"))
        right_layout.addWidget(QLabel("ROLE: ADMIN"))
        add_user = QPushButton("CREATE USER")
        add_user.clicked.connect(self.create_user)
        add_subject = QPushButton("ADD SUBJECT")
        add_subject.clicked.connect(self.add_subject)
        toggle = QPushButton("TOGGLE USER")
        toggle.clicked.connect(self.toggle_user)
        right_layout.addWidget(add_user)
        right_layout.addWidget(add_subject)
        right_layout.addWidget(toggle)
        right_layout.addStretch()

        body.addWidget(left, 3)
        body.addWidget(right, 1)
        outer.addLayout(body)
        self.resize(1300, 800)
        self.refresh()

    def refresh(self):
        self.load_table(self.users_table, ["Username", "Role", "Status", "Created"], [
            (u, r, "ACTIVE" if a else "DISABLED", c)
            for u, r, a, c in fetch_all("SELECT username, role, is_active, created_at FROM users ORDER BY role, username")
        ])
        self.subject_list.clear()
        self.subject_list.addItems(subjects())
        self.load_table(self.audit_table, ["User", "Action", "Details", "Timestamp"], fetch_all(
            "SELECT COALESCE(u.username, 'SYSTEM'), a.action, a.details, a.timestamp FROM audit_log a LEFT JOIN users u ON u.id=a.user_id ORDER BY a.timestamp DESC LIMIT 50"
        ))
        self.log("ADMIN DATA REFRESHED")

    def load_table(self, table, headers, rows):
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                table.setItem(r, c, QTableWidgetItem(str(value)))
        table.resizeColumnsToContents()

    def add_subject(self):
        name, ok = QInputDialog.getText(self, "Add Subject", "Subject name:")
        if ok and name.strip():
            execute("INSERT INTO subjects(name) VALUES (%s)", (name.strip(),))
            log_audit(self.user["id"], "ADD_SUBJECT", f"subject={name.strip()}")
            self.refresh()

    def create_user(self):
        QMessageBox.information(self, "Create User", "Use admin dashboard in the modular project for full guided user creation.")

    def toggle_user(self):
        row = self.users_table.currentRow()
        if row < 0:
            return
        username = self.users_table.item(row, 0).text()
        if username == self.user["username"]:
            QMessageBox.warning(self, "Blocked", "You cannot disable yourself.")
            return
        active = fetch_all("SELECT is_active FROM users WHERE username=%s", (username,))
        if active:
            execute("UPDATE users SET is_active=%s WHERE username=%s", (not bool(active[0][0]), username))
            log_audit(self.user["id"], "TOGGLE_USER", f"username={username}")
            self.refresh()

    def logout(self):
        self.on_logout()
        self.close()


class FacultyWindow(BaseWindow):
    def __init__(self, user: dict, on_logout):
        super().__init__()
        self.user = user
        self.on_logout = on_logout
        self.current_student = None
        self.setWindowTitle("SPA FACULTY DASHBOARD")
        root = QWidget()
        outer = QVBoxLayout(root)
        self.setCentralWidget(root)

        header = QHBoxLayout()
        header.addWidget(QLabel("FACULTY MARKS CONSOLE"))
        header.addStretch()
        logout = QPushButton("LOGOUT")
        logout.clicked.connect(self.logout)
        header.addWidget(logout)
        outer.addLayout(header)

        body = QHBoxLayout()
        left, left_layout = self.panel()
        self.tabs = QTabWidget()
        self.marks_table = QTableWidget()
        self.roster_table = QTableWidget()
        self.subject_list = QListWidget()
        self.tabs.addTab(self.marks_table, "STUDENT MARKS")
        self.tabs.addTab(self.roster_table, "SUBJECT ROSTER")
        self.tabs.addTab(self.subject_list, "SUBJECTS")
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        left_layout.addWidget(self.tabs)
        left_layout.addWidget(self.terminal)

        search_row = QHBoxLayout()
        self.prn = QLineEdit()
        self.prn.setPlaceholderText("STUDENT PRN")
        search = QPushButton("SEARCH")
        search.clicked.connect(self.search_student)
        search_row.addWidget(self.prn)
        search_row.addWidget(search)
        left_layout.addLayout(search_row)

        right, right_layout = self.panel()
        right_layout.addWidget(QLabel(f"USERNAME: {user['username']}"))
        right_layout.addWidget(QLabel("ROLE: FACULTY"))
        self.student_label = QLabel("NO STUDENT LOCKED")
        self.subject_combo = QComboBox()
        self.mark_input = QLineEdit()
        self.mark_input.setPlaceholderText("MARKS 0-100")
        save = QPushButton("SAVE MARK")
        save.clicked.connect(self.save_mark)
        bulk = QPushButton("BULK UPDATE TABLE")
        bulk.clicked.connect(self.bulk_update)
        self.subject_combo.currentTextChanged.connect(self.load_roster)
        right_layout.addWidget(self.student_label)
        right_layout.addWidget(self.subject_combo)
        right_layout.addWidget(self.mark_input)
        right_layout.addWidget(save)
        right_layout.addWidget(bulk)
        right_layout.addStretch()

        body.addWidget(left, 3)
        body.addWidget(right, 1)
        outer.addLayout(body)
        self.resize(1300, 800)
        self.refresh_subjects()

    def refresh_subjects(self):
        rows = fetch_all("SELECT subject_name FROM faculty_subjects WHERE faculty_id=%s ORDER BY subject_name", (self.user["id"],))
        names = [r[0] for r in rows]
        self.subject_list.clear()
        self.subject_list.addItems(names)
        self.subject_combo.clear()
        self.subject_combo.addItems(names)

    def search_student(self):
        rows = fetch_all("SELECT id, name, department, prn FROM students WHERE prn=%s", (self.prn.text().strip(),))
        if not rows:
            QMessageBox.information(self, "Not Found", "Student not found.")
            return
        self.current_student = rows[0]
        self.student_label.setText(f"{rows[0][1]} | {rows[0][2]} | {rows[0][3]}")
        self.load_marks(rows[0][0])

    def load_marks(self, student_id):
        rows = fetch_all("SELECT subject, marks FROM student_marks WHERE student_id=%s ORDER BY subject", (student_id,))
        self.load_table(self.marks_table, ["Subject", "Marks"], rows)

    def load_roster(self, subject):
        if not subject:
            return
        rows = fetch_all(
            """
            SELECT s.id, s.name, s.prn, sm.marks
            FROM students s
            LEFT JOIN student_marks sm ON sm.student_id=s.id AND sm.subject=%s
            ORDER BY s.name
            """,
            (subject,),
        )
        self.load_table(self.roster_table, ["ID", "Student", "PRN", "Marks"], rows)
        self.roster_table.setColumnHidden(0, True)

    def load_table(self, table, headers, rows):
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                table.setItem(r, c, QTableWidgetItem("" if value is None else str(value)))
        table.resizeColumnsToContents()

    def save_mark(self):
        if not self.current_student:
            QMessageBox.information(self, "No Student", "Search a student first.")
            return
        self.upsert_mark(self.current_student[0], self.subject_combo.currentText(), float(self.mark_input.text()))
        self.load_marks(self.current_student[0])
        self.load_roster(self.subject_combo.currentText())

    def upsert_mark(self, student_id, subject, marks):
        if not 0 <= marks <= 100:
            raise ValueError("Marks must be between 0 and 100.")
        exists = fetch_all("SELECT id FROM student_marks WHERE student_id=%s AND subject=%s", (student_id, subject))
        if exists:
            execute("UPDATE student_marks SET marks=%s WHERE student_id=%s AND subject=%s", (marks, student_id, subject))
        else:
            execute("INSERT INTO student_marks(student_id, subject, marks) VALUES (%s, %s, %s)", (student_id, subject, marks))
        log_audit(self.user["id"], "UPSERT_MARKS", f"student_id={student_id} subject={subject} marks={marks}")

    def bulk_update(self):
        subject = self.subject_combo.currentText()
        for row in range(self.roster_table.rowCount()):
            sid = self.roster_table.item(row, 0)
            marks = self.roster_table.item(row, 3)
            if sid and marks and marks.text().strip():
                self.upsert_mark(int(sid.text()), subject, float(marks.text()))
        self.load_roster(subject)
        QMessageBox.information(self, "Bulk Update", "Subject marks updated.")

    def logout(self):
        self.on_logout()
        self.close()


class StudentWindow(BaseWindow):
    def __init__(self, user: dict, on_logout):
        super().__init__()
        self.user = user
        self.on_logout = on_logout
        self.rows = []
        self.gpa = 0
        self.setWindowTitle("SPA STUDENT DASHBOARD")
        root = QWidget()
        layout = QHBoxLayout(root)
        self.setCentralWidget(root)

        left, left_layout = self.panel()
        self.table = QTableWidget()
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        left_layout.addWidget(self.table)
        left_layout.addWidget(self.terminal)

        right, right_layout = self.panel()
        right_layout.addWidget(QLabel(f"USERNAME: {user['username']}"))
        right_layout.addWidget(QLabel("ROLE: STUDENT"))
        self.gpa_label = QLabel("GPA: 0")
        refresh = QPushButton("REFRESH")
        refresh.clicked.connect(self.refresh)
        export = QPushButton("EXPORT CSV")
        export.clicked.connect(self.export_csv)
        logout = QPushButton("LOGOUT")
        logout.clicked.connect(self.logout)
        right_layout.addWidget(self.gpa_label)
        right_layout.addWidget(refresh)
        right_layout.addWidget(export)
        right_layout.addWidget(logout)
        right_layout.addStretch()

        layout.addWidget(left, 3)
        layout.addWidget(right, 1)
        self.resize(1100, 720)
        self.refresh()

    def refresh(self):
        student_id = self.user.get("student_id")
        self.rows = fetch_all("SELECT subject, marks FROM student_marks WHERE student_id=%s ORDER BY subject", (student_id,))
        self.gpa = round(sum(float(r[1]) for r in self.rows) / len(self.rows), 2) if self.rows else 0
        self.gpa_label.setText(f"GPA: {self.gpa}")
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Subject", "Marks"])
        self.table.setRowCount(len(self.rows))
        for r, row in enumerate(self.rows):
            self.table.setItem(r, 0, QTableWidgetItem(str(row[0])))
            self.table.setItem(r, 1, QTableWidgetItem(str(row[1])))
        self.table.resizeColumnsToContents()
        self.log("STUDENT PERFORMANCE FEED REFRESHED")

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", f"{self.user['username']}_report.csv", "CSV Files (*.csv)")
        if not path:
            return
        with Path(path).open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Subject", "Marks"])
            writer.writerows(self.rows)
            writer.writerow([])
            writer.writerow(["Average (GPA)", self.gpa])

    def logout(self):
        self.on_logout()
        self.close()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Student Performance Analyzer")
    app.setStyleSheet(QSS)
    login = LoginWindow()
    login.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
