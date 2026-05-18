import csv
from pathlib import Path

from academic import AcademicService
from db import get_connection
from faculty import FacultyService


class StudentService:
    @staticmethod
    def marks(student_id: int) -> list[tuple]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    sub.name,
                    COALESCE(sm.marks, 'Not Entered') AS marks,
                    CASE
                        WHEN sm.marks IS NULL THEN 'N/A'
                        WHEN sm.marks >= 90 THEN 'A'
                        WHEN sm.marks >= 75 THEN 'B'
                        WHEN sm.marks >= 60 THEN 'C'
                        WHEN sm.marks >= 40 THEN 'D'
                        ELSE 'F'
                    END AS grade,
                    CASE
                        WHEN sm.marks IS NULL THEN 'PENDING'
                        WHEN sm.marks >= 40 THEN 'PASS'
                        ELSE 'FAIL'
                    END AS result
                FROM subjects sub
                LEFT JOIN student_marks sm
                       ON sm.subject = sub.name
                      AND sm.student_id = %s
                ORDER BY sub.name
                """,
                (student_id,),
            )
            rows = cur.fetchall()
            if rows:
                return rows
            return [(subject, marks, AcademicService.grade_from_average(marks), "PASS" if float(marks) >= 40 else "FAIL") for subject, marks in FacultyService.marks(student_id)]
        finally:
            conn.close()

    @staticmethod
    def gpa(rows: list[tuple]) -> float:
        return AcademicService.gpa_from_average(StudentService.average_marks(rows))

    @staticmethod
    def average_marks(rows: list[tuple]) -> float:
        marks = []
        for row in rows:
            try:
                marks.append(float(row[1]))
            except (TypeError, ValueError):
                continue
        if not marks:
            return 0.0
        return round(sum(marks) / len(marks), 2)

    @staticmethod
    def grade(rows: list[tuple]) -> str:
        return AcademicService.grade_from_average(StudentService.average_marks(rows))

    @staticmethod
    def export_csv(path: str | Path, rows: list[tuple], average_marks: float, gpa: float, grade: str) -> None:
        with Path(path).open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Subject", "Marks", "Grade", "Result"])
            writer.writerows(rows)
            writer.writerow([])
            writer.writerow(["Average Marks", average_marks])
            writer.writerow(["GPA", gpa])
            writer.writerow(["Grade", grade])
