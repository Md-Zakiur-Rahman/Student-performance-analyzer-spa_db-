from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow, QMessageBox

from app_paths import resource_path
from db import AuthService


class LoginController(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(resource_path("ui", "login.ui"), self)
        self.dashboard = None
        self.loginButton.clicked.connect(self.login)
        self.passwordInput.returnPressed.connect(self.login)

    def login(self) -> None:
        identifier = self.identifierInput.text().strip()
        password = self.passwordInput.text()

        if not identifier or not password:
            QMessageBox.warning(self, "Input Required", "Username/PRN and password are required.")
            return

        try:
            user = AuthService.authenticate(identifier, password)
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", str(exc))
            return

        if not user:
            self.log("ACCESS DENIED: invalid credentials or inactive account.")
            QMessageBox.warning(self, "Login Failed", "Invalid credentials or inactive account.")
            return

        self.open_dashboard(user)

    def open_dashboard(self, user: dict) -> None:
        role = user["role"]
        if role == "admin":
            from controllers.admin_controller import AdminController

            self.dashboard = AdminController(user, self.return_to_login)
        elif role == "faculty":
            from controllers.faculty_controller import FacultyController

            self.dashboard = FacultyController(user, self.return_to_login)
        elif role == "student":
            from controllers.student_controller import StudentController

            self.dashboard = StudentController(user, self.return_to_login)
        else:
            QMessageBox.critical(self, "Access Denied", f"Unknown role: {role}")
            return

        self.dashboard.show()
        self.hide()

    def return_to_login(self) -> None:
        self.dashboard = None
        self.passwordInput.clear()
        self.identifierInput.clear()
        self.terminalOutput.clear()
        self.terminalOutput.setPlainText("SESSION ENDED\nAUTH CHANNEL READY")
        self.show()
        self.activateWindow()

    def log(self, message: str) -> None:
        self.terminalOutput.append(f"> {message}")
