from pathlib import Path

from PyQt6 import uic
from PyQt6.QtWidgets import QInputDialog, QMainWindow, QMessageBox, QTableWidgetItem

from admin import AdminService


BASE_DIR = Path(__file__).resolve().parents[1]


class AdminController(QMainWindow):
    def __init__(self, user: dict, on_logout=None):
        super().__init__()
        uic.loadUi(BASE_DIR / "ui" / "admin.ui", self)
        self.user = user
        self.on_logout = on_logout
        self.usernameLabel.setText(f"USERNAME: {user['username']}")
        self.roleLabel.setText("ROLE: ADMIN")

        self.refreshButton.clicked.connect(self.refresh)
        self.addSubjectButton.clicked.connect(self.add_subject)
        self.createUserButton.clicked.connect(self.create_user)
        self.toggleUserButton.clicked.connect(self.toggle_selected_user)
        self.logoutButton.clicked.connect(self.logout)
        self.commandInput.returnPressed.connect(self.execute_command)
        self.executeButton.clicked.connect(self.execute_command)
        self.refresh()

    def refresh(self) -> None:
        try:
            self.load_users()
            self.load_subjects()
            self.load_audit()
            self.log("ADMIN DATA REFRESHED")
        except Exception as exc:
            QMessageBox.critical(self, "Refresh Failed", str(exc))

    def log(self, message: str) -> None:
        self.terminalOutput.append(f"> {message}")

    def load_users(self) -> None:
        rows = AdminService.users()
        self.usersTable.setColumnCount(4)
        self.usersTable.setHorizontalHeaderLabels(["Username", "Role", "Status", "Created"])
        self.usersTable.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            username, role, active, created = row
            values = [username, role, "ACTIVE" if active else "DISABLED", str(created)]
            for col, value in enumerate(values):
                self.usersTable.setItem(row_index, col, QTableWidgetItem(str(value)))
        self.usersTable.resizeColumnsToContents()

    def load_subjects(self) -> None:
        self.subjectsList.clear()
        self.subjectsList.addItems(AdminService.subjects())

    def load_audit(self) -> None:
        rows = AdminService.audit_log()
        self.auditTable.setColumnCount(4)
        self.auditTable.setHorizontalHeaderLabels(["User", "Action", "Details", "Timestamp"])
        self.auditTable.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for col, value in enumerate(row):
                self.auditTable.setItem(row_index, col, QTableWidgetItem(str(value)))
        self.auditTable.resizeColumnsToContents()

    def add_subject(self) -> None:
        name, ok = QInputDialog.getText(self, "Add Subject", "Subject name:")
        if not ok or not name.strip():
            return
        try:
            AdminService.add_subject(self.user, name.strip())
            self.log(f"SUBJECT ADDED: {name.strip()}")
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Add Subject Failed", str(exc))

    def create_user(self) -> None:
        role, ok = QInputDialog.getItem(self, "Create User", "Role:", ["admin", "faculty", "student"], editable=False)
        if not ok:
            return

        username, ok = QInputDialog.getText(self, "Create User", "Username (blank auto-generates students):")
        if not ok:
            return
        password, ok = QInputDialog.getText(self, "Create User", "Password (blank uses student username):")
        if not ok:
            return

        name = department = prn = ""
        subjects = []
        if role == "student":
            name, ok = QInputDialog.getText(self, "Create Student", "Full name:")
            if not ok:
                return
            department, ok = QInputDialog.getText(self, "Create Student", "Department:")
            if not ok:
                return
            prn, ok = QInputDialog.getText(self, "Create Student", "PRN:")
            if not ok:
                return
        elif role == "faculty":
            available = AdminService.subjects()
            if not available:
                QMessageBox.warning(self, "No Subjects", "Add subjects before creating faculty users.")
                return
            selected, ok = QInputDialog.getText(self, "Assign Subjects", "Comma-separated subjects:", text=", ".join(available[:1]))
            if not ok:
                return
            subjects = [item.strip() for item in selected.split(",") if item.strip() in available]

        try:
            actual_username, actual_password = AdminService.create_user(
                self.user, role, username.strip(), password, name.strip(), department.strip(), prn.strip(), subjects
            )
            self.log(f"USER CREATED: {actual_username} / {role} / password={actual_password}")
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Create User Failed", str(exc))

    def toggle_selected_user(self) -> None:
        row = self.usersTable.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select User", "Select a user row first.")
            return
        username = self.usersTable.item(row, 0).text()
        try:
            active = AdminService.toggle_user(self.user, username)
            self.log(f"USER STATUS: {username} -> {'ACTIVE' if active else 'DISABLED'}")
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Toggle Failed", str(exc))

    def execute_command(self) -> None:
        command = self.commandInput.text().strip().lower()
        self.commandInput.clear()
        if command in {"refresh", "reload"}:
            self.refresh()
        elif command == "subjects":
            self.tabs.setCurrentWidget(self.subjectsTab)
        elif command == "users":
            self.tabs.setCurrentWidget(self.usersTab)
        elif command == "audit":
            self.tabs.setCurrentWidget(self.auditTab)
        else:
            self.log(f"UNKNOWN COMMAND: {command or '<empty>'}")

    def logout(self) -> None:
        if self.on_logout:
            self.on_logout()
        self.close()
