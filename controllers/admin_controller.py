from PyQt6 import uic
from PyQt6.QtWidgets import QAbstractItemView
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from academic import AcademicService
from app_paths import resource_path
from admin import AdminService


class AdminController(QMainWindow):
    def __init__(self, user: dict, on_logout=None):
        super().__init__()
        uic.loadUi(resource_path("ui", "admin.ui"), self)
        self.user = user
        self.on_logout = on_logout
        self.usernameLabel.setText(f"USERNAME: {user['username']}")
        self.roleLabel.setText("ROLE: ADMIN")

        self.refreshButton.clicked.connect(self.refresh)
        self.addSubjectButton.clicked.connect(self.add_subject)
        self.createUserButton.clicked.connect(self.create_user)
        self.toggleUserButton.clicked.connect(self.toggle_selected_user)
        self.setup_feature_tabs()
        self.setup_admin_actions()
        self.logoutButton.clicked.connect(self.logout)
        self.commandInput.returnPressed.connect(self.execute_command)
        self.executeButton.clicked.connect(self.execute_command)
        self.refresh()

    def setup_feature_tabs(self) -> None:
        self.dashboardTable = QTableWidget()
        self.tabs.insertTab(0, self.dashboardTable, "DASHBOARD")

        self.studentsTab = QWidget()
        students_layout = QHBoxLayout(self.studentsTab)
        self.departmentInput = QLineEdit()
        self.departmentInput.setPlaceholderText("DEPARTMENT FILTER")
        self.searchDepartmentButton = QPushButton("SEARCH")
        self.addBonusButton = QPushButton("ADD BONUS")
        self.exportHighButton = QPushButton("EXPORT HIGH CSV")
        self.mysqlUsersButton = QPushButton("CREATE MYSQL USERS")
        self.studentsTable = QTableWidget()
        side = QWidget()
        side_layout = QVBoxLayout(side)
        for widget in (
            self.departmentInput,
            self.searchDepartmentButton,
            self.addBonusButton,
            self.exportHighButton,
            self.mysqlUsersButton,
        ):
            side_layout.addWidget(widget)
        side_layout.addStretch()
        students_layout.addWidget(self.studentsTable, 5)
        students_layout.addWidget(side, 2)
        self.tabs.addTab(self.studentsTab, "STUDENTS")

        self.analyticsTable = QTableWidget()
        self.tabs.addTab(self.analyticsTable, "ANALYTICS")
        self.leaderboardTable = QTableWidget()
        self.tabs.addTab(self.leaderboardTable, "LEADERBOARD")

        self.searchDepartmentButton.clicked.connect(self.load_students)
        self.departmentInput.returnPressed.connect(self.load_students)
        self.addBonusButton.clicked.connect(self.add_bonus_marks)
        self.exportHighButton.clicked.connect(self.export_high_performers)
        self.mysqlUsersButton.clicked.connect(self.create_mysql_users)

    def choose_subjects(self, title: str, available: list[str], selected: list[str] | None = None) -> list[str] | None:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)

        list_widget = QListWidget()
        list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        selected_set = set(selected or [])
        for subject in available:
            item = QListWidgetItem(subject)
            if subject in selected_set:
                item.setSelected(True)
            list_widget.addItem(item)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(list_widget)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return [item.text() for item in list_widget.selectedItems()]

    def setup_admin_actions(self) -> None:
        self.editUserButton = QPushButton("EDIT USER")
        self.deleteUserButton = QPushButton("DELETE USER")
        self.editSubjectButton = QPushButton("EDIT SUBJECT")
        self.deleteSubjectButton = QPushButton("DELETE SUBJECT")

        self.rightLayout.insertWidget(4, self.editUserButton)
        self.rightLayout.insertWidget(5, self.deleteUserButton)
        self.rightLayout.insertWidget(7, self.editSubjectButton)
        self.rightLayout.insertWidget(8, self.deleteSubjectButton)

        self.editUserButton.clicked.connect(self.edit_selected_user)
        self.deleteUserButton.clicked.connect(self.delete_selected_user)
        self.editSubjectButton.clicked.connect(self.edit_selected_subject)
        self.deleteSubjectButton.clicked.connect(self.delete_selected_subject)

    def refresh(self) -> None:
        try:
            self.load_users()
            self.load_subjects()
            self.load_audit()
            self.load_dashboard()
            self.load_students()
            self.load_analytics()
            self.load_leaderboard()
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

    def load_table(self, table: QTableWidget, headers: list[str], rows: list[tuple]) -> None:
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for col, value in enumerate(row):
                table.setItem(row_index, col, QTableWidgetItem(str(value)))
        table.resizeColumnsToContents()

    def load_dashboard(self) -> None:
        self.load_table(
            self.dashboardTable,
            ["Name", "PRN", "Department", "Subject", "Marks", "Average", "GPA", "Grade", "Result"],
            AcademicService.dashboard_subject_marks(),
        )

    def load_students(self) -> None:
        rows = AcademicService.students(self.departmentInput.text())
        self.load_table(self.studentsTable, ["ID", "Name", "Department", "PRN", "Average", "GPA", "Grade", "Subjects"], rows)
        self.studentsTable.setColumnHidden(0, True)

    def load_analytics(self) -> None:
        self.load_table(
            self.analyticsTable,
            ["Report", "Field 1", "Field 2", "Field 3", "Field 4", "Field 5", "Field 6"],
            AcademicService.analytics_dashboard_rows(),
        )

    def load_leaderboard(self) -> None:
        self.load_table(
            self.leaderboardTable,
            ["Rank", "Name", "PRN", "Department", "Average", "GPA", "Grade", "Subjects"],
            AcademicService.top_performers(),
        )

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

    def selected_subject(self) -> str | None:
        item = self.subjectsList.currentItem()
        if not item:
            QMessageBox.information(self, "Select Subject", "Select a subject first.")
            return None
        return item.text()

    def edit_selected_subject(self) -> None:
        old_name = self.selected_subject()
        if not old_name:
            return
        new_name, ok = QInputDialog.getText(self, "Edit Subject", "Subject name:", text=old_name)
        if not ok or not new_name.strip():
            return
        try:
            AdminService.update_subject(self.user, old_name, new_name.strip())
            self.log(f"SUBJECT UPDATED: {old_name} -> {new_name.strip()}")
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Edit Subject Failed", str(exc))

    def delete_selected_subject(self) -> None:
        name = self.selected_subject()
        if not name:
            return
        if QMessageBox.question(self, "Delete Subject", f"Delete subject '{name}'? Existing marks for this subject must be removed first.") != QMessageBox.StandardButton.Yes:
            return
        try:
            AdminService.delete_subject(self.user, name)
            self.log(f"SUBJECT DELETED: {name}")
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Delete Subject Failed", str(exc))

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
            subjects = self.choose_subjects("Assign Subjects", available)
            if subjects is None:
                return
            if not subjects:
                QMessageBox.warning(self, "No Subjects Selected", "Select at least one subject for faculty users.")
                return

        try:
            actual_username, actual_password = AdminService.create_user(
                self.user, role, username.strip(), password, name.strip(), department.strip(), prn.strip(), subjects
            )
            self.log(f"USER CREATED: {actual_username} / {role} / password={actual_password}")
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Create User Failed", str(exc))

    def add_bonus_marks(self) -> None:
        department, ok = QInputDialog.getText(self, "Add Bonus Marks", "Department:")
        if not ok or not department.strip():
            return
        bonus, ok = QInputDialog.getDouble(self, "Add Bonus Marks", "Bonus marks for department:", 1, 0.1, 100, 2)
        if not ok:
            return
        try:
            affected = AcademicService.add_bonus_marks(self.user, department.strip(), bonus)
            self.log(f"BONUS APPLIED: {department.strip()} +{bonus} affected={affected}")
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Bonus Failed", str(exc))

    def export_high_performers(self) -> None:
        default_path = str(AcademicService.timestamped_export_path("high_performers.csv"))
        path, _ = QFileDialog.getSaveFileName(self, "Export High Performers", default_path, "CSV Files (*.csv)")
        if not path:
            return
        try:
            export_path = AcademicService.export_high_performers(path)
            self.log(f"HIGH PERFORMERS EXPORTED: {export_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))

    def create_mysql_users(self) -> None:
        try:
            AdminService.create_mysql_application_users(self.user)
            self.log("MYSQL APPLICATION USERS CREATED/UPDATED")
        except Exception as exc:
            QMessageBox.critical(self, "MySQL User Setup Failed", str(exc))

    def selected_username(self) -> str | None:
        row = self.usersTable.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select User", "Select a user row first.")
            return None
        return self.usersTable.item(row, 0).text()

    def edit_selected_user(self) -> None:
        username = self.selected_username()
        if not username:
            return

        row = AdminService.user(username)
        if not row:
            QMessageBox.warning(self, "User Missing", f"User '{username}' was not found.")
            return
        _, current_username, role, _ = row

        new_username, ok = QInputDialog.getText(self, "Edit User", "Username:", text=current_username)
        if not ok or not new_username.strip():
            return
        new_password, ok = QInputDialog.getText(self, "Edit User", "New password (blank keeps current):")
        if not ok:
            return

        subjects = None
        student_profile = None
        if role == "faculty":
            available = AdminService.subjects()
            if not available:
                QMessageBox.warning(self, "No Subjects", "Add subjects before editing faculty assignments.")
                return
            assigned = AdminService.faculty_subjects(username)
            subjects = self.choose_subjects("Assign Subjects", available, assigned)
            if subjects is None:
                return
            if not subjects:
                QMessageBox.warning(self, "No Subjects Selected", "Select at least one subject for faculty users.")
                return
        elif role == "student":
            profile = AdminService.student_profile(username)
            name, department, prn = profile if profile else ("", "", "")
            name, ok = QInputDialog.getText(self, "Edit Student Profile", "Full name:", text=name)
            if not ok:
                return
            department, ok = QInputDialog.getText(self, "Edit Student Profile", "Department:", text=department)
            if not ok:
                return
            prn, ok = QInputDialog.getText(self, "Edit Student Profile", "PRN:", text=prn)
            if not ok:
                return
            student_profile = (name.strip(), department.strip(), prn.strip())

        try:
            AdminService.update_user(self.user, username, new_username.strip(), new_password, subjects, student_profile)
            self.log(f"USER UPDATED: {username} -> {new_username.strip()}")
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Edit User Failed", str(exc))

    def delete_selected_user(self) -> None:
        username = self.selected_username()
        if not username:
            return
        if QMessageBox.question(self, "Delete User", f"Delete user '{username}' and any linked student/faculty data?") != QMessageBox.StandardButton.Yes:
            return
        try:
            AdminService.delete_user(self.user, username)
            self.log(f"USER DELETED: {username}")
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Delete User Failed", str(exc))

    def toggle_selected_user(self) -> None:
        username = self.selected_username()
        if not username:
            return
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
        elif command == "students":
            self.tabs.setCurrentWidget(self.studentsTab)
        elif command == "analytics":
            self.tabs.setCurrentWidget(self.analyticsTable)
        elif command in {"leaderboard", "top"}:
            self.tabs.setCurrentWidget(self.leaderboardTable)
        else:
            self.log(f"UNKNOWN COMMAND: {command or '<empty>'}")

    def logout(self) -> None:
        if self.on_logout:
            self.on_logout()
        self.close()
