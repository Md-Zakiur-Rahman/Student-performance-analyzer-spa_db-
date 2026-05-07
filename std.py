import csv
from pathlib import Path

from faculty import FacultyService


class StudentService:
    @staticmethod
    def marks(student_id: int) -> list[tuple]:
        return FacultyService.marks(student_id)

    @staticmethod
    def gpa(rows: list[tuple]) -> float:
        if not rows:
            return 0.0
        return round(sum(float(row[1]) for row in rows) / len(rows), 2)

    @staticmethod
    def export_csv(path: str | Path, rows: list[tuple], gpa: float) -> None:
        with Path(path).open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Subject", "Marks"])
            writer.writerows(rows)
            writer.writerow([])
            writer.writerow(["Average (GPA)", gpa])
