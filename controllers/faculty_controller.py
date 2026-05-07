from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QTableWidgetItem

from faculty import FacultyService


BASE_DIR = Path(__file__).resolve().parents[1]


class FacultyController(QMainWindow):
    def __init__(self, user: dict, on_logout=None):
        super().__init__()
        uic.loadUi(BASE_DIR / "ui" / "faculty.ui", self)
        self.user = user
        self.on_logout = on_logout
        self.current_student = None
        self.usernameLabel.setText(f"USERNAME: {user['username']}")
        self.roleLabel.setText("ROLE: FACULTY")
        self.searchButton.clicked.connect(self.search_student)
        self.saveMarkButton.clicked.connect(self.save_mark)
        self.bulkUpdateButton.clicked.connect(self.bulk_update_marks)
        self.refreshButton.clicked.connect(self.refresh_subjects)
        self.logoutButton.clicked.connect(self.logout)
        self.prnInput.returnPressed.connect(self.search_student)
        self.subjectCombo.currentTextChanged.connect(self.load_subject_roster)
        self.refresh_subjects()

    def refresh_subjects(self) -> None:
        try:
            self.subjectsList.clear()
            subjects = FacultyService.assigned_subjects(self.user["id"])
            self.subjectsList.addItems(subjects)
            self.subjectCombo.clear()
            self.subjectCombo.addItems(subjects)
            if subjects:
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

            for row_index, (student_id, name, prn, marks) in enumerate(rows):
                values = [student_id, name, prn, "" if marks is None else marks]
                for col, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    if col in {0, 1, 2}:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.subjectRosterTable.setItem(row_index, col, item)

            self.subjectRosterTable.resizeColumnsToContents()
            self.log(f"ROSTER LOADED: {subject}")
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
            self.log(f"BULK UPDATE COMPLETE: {subject} | updated={updated} inserted={inserted}")
            self.load_subject_roster(subject)
            if self.current_student:
                self.load_marks(self.current_student[0])
        except Exception as exc:
            QMessageBox.critical(self, "Bulk Update Failed", str(exc))

    def logout(self) -> None:
        if self.on_logout:
            self.on_logout()
        self.close()
