from PyQt6 import uic
from PyQt6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QTableWidget, QTableWidgetItem

from academic import AcademicService
from app_paths import resource_path
from std import StudentService


class StudentController(QMainWindow):
    def __init__(self, user: dict, on_logout=None):
        super().__init__()
        uic.loadUi(resource_path("ui", "student.ui"), self)
        self.user = user
        self.on_logout = on_logout
        self.rows = []
        self.average_marks = 0.0
        self.gpa = 0.0
        self.grade = "F"
        self.usernameLabel.setText(f"USERNAME: {user['username']}")
        self.roleLabel.setText("ROLE: STUDENT")
        self.statusLabel.setWordWrap(True)
        self.analyticsTable = QTableWidget()
        self.tabs.addTab(self.analyticsTable, "ANALYTICS")
        self.leaderboardTable = QTableWidget()
        self.tabs.addTab(self.leaderboardTable, "LEADERBOARD")
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
            profile = AcademicService.student_profile(student_id)
            self.rows = StudentService.marks(student_id)
            self.average_marks = StudentService.average_marks(self.rows)
            self.gpa = StudentService.gpa(self.rows)
            self.grade = StudentService.grade(self.rows)
            if profile:
                _, name, department, prn, average_marks, gpa, grade, subject_count = profile
                self.average_marks = float(average_marks)
                self.gpa = float(gpa)
                self.grade = grade
                self.statusLabel.setText(
                    f"STATUS: ONLINE\nNAME: {name}\nDEPARTMENT: {department}\nPRN: {prn}\nSUBJECTS MARKED: {subject_count}"
                )
            self.gpaLabel.setText(f"GPA (MAX 10): {self.gpa} | AVG: {self.average_marks} | GRADE: {self.grade}")
            self.marksTable.setColumnCount(4)
            self.marksTable.setHorizontalHeaderLabels(["Subject", "Marks", "Grade", "Result"])
            self.marksTable.setRowCount(len(self.rows))
            for row_index, row in enumerate(self.rows):
                for col, value in enumerate(row):
                    self.marksTable.setItem(row_index, col, QTableWidgetItem(str(value)))
            self.marksTable.resizeColumnsToContents()
            self.load_analytics()
            self.load_leaderboard()
            self.log("STUDENT PERFORMANCE FEED REFRESHED")
        except Exception as exc:
            QMessageBox.critical(self, "Refresh Failed", str(exc))

    def load_table(self, table: QTableWidget, headers: list[str], rows: list[tuple]) -> None:
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for col, value in enumerate(row):
                table.setItem(row_index, col, QTableWidgetItem(str(value)))
        table.resizeColumnsToContents()

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

    def log(self, message: str) -> None:
        self.terminalOutput.append(f"> {message}")

    def export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", f"{self.user['username']}_report.csv", "CSV Files (*.csv)")
        if not path:
            return
        try:
            StudentService.export_csv(path, self.rows, self.average_marks, self.gpa, self.grade)
            self.log(f"CSV EXPORTED: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))

    def logout(self) -> None:
        if self.on_logout:
            self.on_logout()
        self.close()
