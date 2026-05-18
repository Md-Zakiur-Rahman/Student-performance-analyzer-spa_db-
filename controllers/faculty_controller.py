from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
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
from faculty import FacultyService


class FacultyController(QMainWindow):
    def __init__(self, user: dict, on_logout=None):
        super().__init__()
        uic.loadUi(resource_path("ui", "faculty.ui"), self)
        self.user = user
        self.on_logout = on_logout
        self.current_student = None
        self.usernameLabel.setText(f"USERNAME: {user['username']}")
        self.roleLabel.setText("ROLE: FACULTY")
        self.setup_feature_tabs()
        self.searchButton.clicked.connect(self.search_student)
        self.saveMarkButton.clicked.connect(self.save_mark)
        self.bulkUpdateButton.clicked.connect(self.bulk_update_marks)
        self.refreshButton.clicked.connect(self.refresh_subjects)
        self.logoutButton.clicked.connect(self.logout)
        self.prnInput.returnPressed.connect(self.search_student)
        self.subjectCombo.currentTextChanged.connect(self.load_subject_roster)
        self.refresh_subjects()

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
        self.studentsTable = QTableWidget()
        action_bar = QWidget()
        action_layout = QVBoxLayout(action_bar)
        for widget in (
            self.departmentInput,
            self.searchDepartmentButton,
            self.addBonusButton,
            self.exportHighButton,
        ):
            action_layout.addWidget(widget)
        action_layout.addStretch()
        students_layout.addWidget(self.studentsTable, 5)
        students_layout.addWidget(action_bar, 2)
        self.tabs.addTab(self.studentsTab, "STUDENTS")

        self.analyticsTable = QTableWidget()
        self.tabs.addTab(self.analyticsTable, "ANALYTICS")
        self.leaderboardTable = QTableWidget()
        self.tabs.addTab(self.leaderboardTable, "LEADERBOARD")

        self.searchDepartmentButton.clicked.connect(self.load_students)
        self.departmentInput.returnPressed.connect(self.load_students)
        self.addBonusButton.clicked.connect(self.add_bonus_marks)
        self.exportHighButton.clicked.connect(self.export_high_performers)

    def refresh_subjects(self) -> None:
        try:
            self.subjectsList.clear()
            subjects = FacultyService.assigned_subjects(self.user["id"])
            self.subjectsList.addItems(subjects)
            self.subjectCombo.clear()
            self.subjectCombo.addItems(subjects)
            self.load_dashboard()
            self.load_students()
            self.load_analytics()
            self.load_leaderboard()
            if subjects:
                self.tabs.setCurrentWidget(self.rosterTab)
                self.load_subject_roster(subjects[0])
            self.log("SUBJECT RESTRICTIONS LOADED")
        except Exception as exc:
            QMessageBox.critical(self, "Subject Load Failed", str(exc))

    def log(self, message: str) -> None:
        self.terminalOutput.append(f"> {message}")

    def search_student(self) -> None:
        prn = self.prnInput.text().strip()
        if not prn:
            return
        try:
            student = FacultyService.find_student_by_prn(prn)
            if not student:
                self.current_student = None
                self.studentInfoLabel.setText("NO STUDENT LOCKED")
                self.marksTable.setRowCount(0)
                self.log(f"NO STUDENT FOUND FOR PRN {prn}")
                return
            self.current_student = student
            self.studentInfoLabel.setText(f"{student[1]} | {student[2]} | PRN {student[3]}")
            self.load_marks(student[0])
            self.log(f"STUDENT LOCKED: {student[1]}")
        except Exception as exc:
            QMessageBox.critical(self, "Search Failed", str(exc))

    def load_marks(self, student_id: int) -> None:
        rows = FacultyService.marks(student_id)
        self.marksTable.setColumnCount(2)
        self.marksTable.setHorizontalHeaderLabels(["Subject", "Marks"])
        self.marksTable.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for col, value in enumerate(row):
                self.marksTable.setItem(row_index, col, QTableWidgetItem(str(value)))
        self.marksTable.resizeColumnsToContents()

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

    def save_mark(self) -> None:
        if not self.current_student:
            QMessageBox.information(self, "No Student", "Search and lock a student first.")
            return
        subject = self.subjectCombo.currentText()
        try:
            marks = float(self.marksInput.text())
            FacultyService.upsert_mark(self.user, self.current_student[0], subject, marks)
            self.log(f"MARK SAVED: {self.current_student[1]} | {subject} -> {marks}")
            self.load_marks(self.current_student[0])
            self.load_subject_roster(subject)
            self.marksInput.clear()
        except Exception as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))

    def load_subject_roster(self, subject: str) -> None:
        if not subject:
            self.subjectRosterTable.setRowCount(0)
            return

        try:
            rows = FacultyService.subject_roster(self.user["id"], subject)
            self.subjectRosterTable.setColumnCount(4)
            self.subjectRosterTable.setHorizontalHeaderLabels(["ID", "Student", "PRN", "Marks"])
            self.subjectRosterTable.setRowCount(len(rows))
            self.subjectRosterTable.setColumnHidden(0, True)
            self.subjectRosterTable.setSortingEnabled(False)

            for row_index, (student_id, name, prn, marks) in enumerate(rows):
                values = [student_id, name, prn, "" if marks is None else marks]
                for col, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    if col in {0, 1, 2}:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.subjectRosterTable.setItem(row_index, col, item)

            self.subjectRosterTable.resizeColumnsToContents()
            self.tabs.setCurrentWidget(self.rosterTab)
            self.log(f"ROSTER LOADED FOR SUBJECT: {subject}")
        except Exception as exc:
            QMessageBox.critical(self, "Roster Load Failed", str(exc))

    def bulk_update_marks(self) -> None:
        subject = self.subjectCombo.currentText()
        if not subject:
            QMessageBox.information(self, "No Subject", "Select a subject first.")
            return

        updates = []
        try:
            for row in range(self.subjectRosterTable.rowCount()):
                id_item = self.subjectRosterTable.item(row, 0)
                marks_item = self.subjectRosterTable.item(row, 3)
                if not id_item or not marks_item:
                    continue
                raw_marks = marks_item.text().strip()
                if not raw_marks:
                    continue
                updates.append((int(id_item.text()), float(raw_marks)))

            if not updates:
                QMessageBox.information(self, "No Marks", "Enter marks in the roster table first.")
                return

            updated, inserted = FacultyService.bulk_update_marks(self.user, subject, updates)
            self.log(f"SUBJECT MARKS SAVED: {subject} | updated={updated} inserted={inserted}")
            self.load_subject_roster(subject)
            if self.current_student:
                self.load_marks(self.current_student[0])
        except Exception as exc:
            QMessageBox.critical(self, "Bulk Update Failed", str(exc))

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
            self.refresh_subjects()
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

    def logout(self) -> None:
        if self.on_logout:
            self.on_logout()
        self.close()
