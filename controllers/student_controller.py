from pathlib import Path

from PyQt6 import uic
from PyQt6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QTableWidgetItem

from std import StudentService


BASE_DIR = Path(__file__).resolve().parents[1]


class StudentController(QMainWindow):
    def __init__(self, user: dict, on_logout=None):
        super().__init__()
        uic.loadUi(BASE_DIR / "ui" / "student.ui", self)
        self.user = user
        self.on_logout = on_logout
        self.rows = []
        self.gpa = 0.0
        self.usernameLabel.setText(f"USERNAME: {user['username']}")
        self.roleLabel.setText("ROLE: STUDENT")
        self.refreshButton.clicked.connect(self.refresh)
        self.exportButton.clicked.connect(self.export_csv)
        self.logoutButton.clicked.connect(self.logout)
        self.refresh()

    def refresh(self) -> None:
        student_id = self.user.get("student_id")
        if not student_id:
            QMessageBox.critical(self, "Profile Error", "No student profile is linked to this account.")
            return
        try:
            self.rows = StudentService.marks(student_id)
            self.gpa = StudentService.gpa(self.rows)
            self.gpaLabel.setText(f"GPA: {self.gpa}")
            self.marksTable.setColumnCount(2)
            self.marksTable.setHorizontalHeaderLabels(["Subject", "Marks"])
            self.marksTable.setRowCount(len(self.rows))
            for row_index, row in enumerate(self.rows):
                for col, value in enumerate(row):
                    self.marksTable.setItem(row_index, col, QTableWidgetItem(str(value)))
            self.marksTable.resizeColumnsToContents()
            self.log("STUDENT PERFORMANCE FEED REFRESHED")
        except Exception as exc:
            QMessageBox.critical(self, "Refresh Failed", str(exc))

    def log(self, message: str) -> None:
        self.terminalOutput.append(f"> {message}")

    def export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", f"{self.user['username']}_report.csv", "CSV Files (*.csv)")
        if not path:
            return
        try:
            StudentService.export_csv(path, self.rows, self.gpa)
            self.log(f"CSV EXPORTED: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))

    def logout(self) -> None:
        if self.on_logout:
            self.on_logout()
        self.close()
