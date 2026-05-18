import csv
import re
from datetime import datetime
from pathlib import Path

from db import get_connection, hash_password, log_audit


class AcademicService:
    @staticmethod
    def gpa_from_average(average_marks: float) -> float:
        return round(float(average_marks or 0) / 10, 2)

    @staticmethod
    def grade_from_average(average_marks: float) -> str:
        average = float(average_marks or 0)
        if average >= 90:
            return "A"
        if average >= 75:
            return "B"
        if average >= 60:
            return "C"
        if average >= 40:
            return "D"
        return "F"

    @staticmethod
    def grade_scale() -> str:
        return "A (>= 90), B (75-89), C (60-74), D (40-59), F (< 40)"

    @staticmethod
    def dashboard_stats() -> list[tuple[str, str]]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM students),
                    COALESCE((SELECT ROUND(AVG(marks), 2) FROM student_marks), 0),
                    COALESCE((SELECT MAX(marks) FROM student_marks), 0),
                    COALESCE((SELECT MIN(marks) FROM student_marks), 0),
                    (SELECT COUNT(*) FROM subjects)
                """
            )
            total, avg, high, low, subjects = cur.fetchone()
            return [
                ("Total Students", total),
                ("Total Subjects", subjects),
                ("Average Marks", avg),
                ("Average GPA (Max 10)", AcademicService.gpa_from_average(avg)),
                ("Highest Marks", high),
                ("Lowest Marks", low),
                ("Grade Scale", AcademicService.grade_scale()),
            ]
        finally:
            conn.close()

    @staticmethod
    def grade_distribution() -> list[tuple[str, int]]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT 'A (>= 90)', SUM(CASE WHEN marks >= 90 THEN 1 ELSE 0 END) FROM student_marks
                UNION ALL
                SELECT 'B (75-89)', SUM(CASE WHEN marks >= 75 AND marks < 90 THEN 1 ELSE 0 END) FROM student_marks
                UNION ALL
                SELECT 'C (60-74)', SUM(CASE WHEN marks >= 60 AND marks < 75 THEN 1 ELSE 0 END) FROM student_marks
                UNION ALL
                SELECT 'D (40-59)', SUM(CASE WHEN marks >= 40 AND marks < 60 THEN 1 ELSE 0 END) FROM student_marks
                UNION ALL
                SELECT 'F (< 40)', SUM(CASE WHEN marks < 40 THEN 1 ELSE 0 END) FROM student_marks
                """
            )
            return [(label, int(count or 0)) for label, count in cur.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def department_stats() -> list[tuple]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    s.department,
                    COUNT(DISTINCT s.id) AS students,
                    COALESCE(ROUND(AVG(sm.marks), 2), 0) AS average_marks,
                    COALESCE(MAX(sm.marks), 0) AS highest_marks,
                    COALESCE(MIN(sm.marks), 0) AS lowest_marks
                FROM students s
                LEFT JOIN student_marks sm ON sm.student_id = s.id
                GROUP BY s.department
                ORDER BY s.department
                """
            )
            return cur.fetchall()
        finally:
            conn.close()

    @staticmethod
    def department_leaderboard() -> list[tuple]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    s.department,
                    COUNT(DISTINCT s.id) AS students,
                    COALESCE(ROUND(AVG(sm.marks), 2), 0) AS average_marks
                FROM students s
                LEFT JOIN student_marks sm ON sm.student_id = s.id
                GROUP BY s.department
                ORDER BY average_marks DESC, s.department
                """
            )
            return cur.fetchall()
        finally:
            conn.close()

    @staticmethod
    def subject_grade_report() -> list[tuple]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    sub.name AS subject,
                    s.name,
                    s.prn,
                    s.department,
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
                FROM students s
                CROSS JOIN subjects sub
                LEFT JOIN student_marks sm
                       ON sm.student_id = s.id
                      AND sm.subject = sub.name
                ORDER BY sub.name, sm.marks DESC, s.name
                """
            )
            return cur.fetchall()
        finally:
            conn.close()

    @staticmethod
    def analytics_dashboard_rows() -> list[tuple]:
        rows = []
        for metric, value in AcademicService.dashboard_stats():
            rows.append(("Summary", metric, value, "", "", "", ""))
        for grade, count in AcademicService.grade_distribution():
            rows.append(("Marks Distribution", grade, count, "", "", "", ""))
        for department, students, avg, high, low in AcademicService.department_stats():
            rows.append(("Department Stats", department, f"students={students}", f"avg={avg}", f"high={high}", f"low={low}", ""))
        for rank, (department, students, avg) in enumerate(AcademicService.department_leaderboard(), start=1):
            rows.append(("Department Leaderboard", f"#{rank}", department, f"students={students}", f"avg={avg}", "", ""))
        for subject, name, prn, department, marks, grade, result in AcademicService.subject_grade_report():
            rows.append(("Subject Grades", subject, name, prn, department, marks, f"{grade} / {result}"))
        return rows

    @staticmethod
    def dashboard_subject_marks() -> list[tuple]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    s.name,
                    s.prn,
                    s.department,
                    sub.name AS subject,
                    COALESCE(sm.marks, 'Not Entered') AS marks,
                    COALESCE(student_summary.average_marks, 0) AS average_marks,
                    ROUND(COALESCE(student_summary.average_marks, 0) / 10, 2) AS gpa,
                    CASE
                        WHEN COALESCE(student_summary.average_marks, 0) >= 90 THEN 'A'
                        WHEN COALESCE(student_summary.average_marks, 0) >= 75 THEN 'B'
                        WHEN COALESCE(student_summary.average_marks, 0) >= 60 THEN 'C'
                        WHEN COALESCE(student_summary.average_marks, 0) >= 40 THEN 'D'
                        ELSE 'F'
                    END AS grade,
                    CASE
                        WHEN sm.marks IS NULL THEN 'PENDING'
                        WHEN sm.marks >= 40 THEN 'PASS'
                        ELSE 'FAIL'
                    END AS result
                FROM students s
                CROSS JOIN subjects sub
                LEFT JOIN student_marks sm
                       ON sm.student_id = s.id
                      AND sm.subject = sub.name
                LEFT JOIN (
                    SELECT
                        student_id,
                        COALESCE(ROUND(AVG(marks), 2), 0) AS average_marks
                    FROM student_marks
                    GROUP BY student_id
                ) student_summary ON student_summary.student_id = s.id
                ORDER BY s.department, s.name, sub.name
                """
            )
            return cur.fetchall()
        finally:
            conn.close()

    @staticmethod
    def students(department: str = "") -> list[tuple]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            pattern = f"%{department.strip()}%"
            cur.execute(
                """
                SELECT
                    s.id,
                    s.name,
                    s.department,
                    s.prn,
                    COALESCE(ROUND(AVG(sm.marks), 2), 0) AS average_marks,
                    COUNT(sm.id) AS subject_count
                FROM students s
                LEFT JOIN student_marks sm ON sm.student_id = s.id
                WHERE %s = '' OR s.department LIKE %s
                GROUP BY s.id, s.name, s.department, s.prn
                ORDER BY s.department, s.name
                """,
                (department.strip(), pattern),
            )
            return [
                (
                    student_id,
                    name,
                    student_department,
                    prn,
                    average_marks,
                    AcademicService.gpa_from_average(average_marks),
                    AcademicService.grade_from_average(average_marks),
                    subject_count,
                )
                for student_id, name, student_department, prn, average_marks, subject_count in cur.fetchall()
            ]
        finally:
            conn.close()

    @staticmethod
    def student_leaderboard(limit: int | None = None) -> list[tuple]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            query = """
                SELECT
                    s.name,
                    s.prn,
                    s.department,
                    COALESCE(ROUND(AVG(sm.marks), 2), 0) AS average_marks,
                    COUNT(sm.id) AS subject_count
                FROM students s
                LEFT JOIN student_marks sm ON sm.student_id = s.id
                GROUP BY s.id, s.name, s.prn, s.department
                ORDER BY average_marks DESC, s.name
                """
            params = ()
            if limit is not None:
                query += " LIMIT %s"
                params = (limit,)
            cur.execute(query, params)
            rows = cur.fetchall()
            return [
                (
                    rank,
                    name,
                    prn,
                    department,
                    average_marks,
                    AcademicService.gpa_from_average(average_marks),
                    AcademicService.grade_from_average(average_marks),
                    subject_count,
                )
                for rank, (name, prn, department, average_marks, subject_count) in enumerate(rows, start=1)
            ]
        finally:
            conn.close()

    @staticmethod
    def top_performers(limit: int | None = None) -> list[tuple]:
        return AcademicService.student_leaderboard(limit)

    @staticmethod
    def student_profile(student_id: int) -> tuple | None:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    s.id,
                    s.name,
                    s.department,
                    s.prn,
                    COALESCE(ROUND(AVG(sm.marks), 2), 0) AS average_marks,
                    COUNT(sm.id) AS subject_count
                FROM students s
                LEFT JOIN student_marks sm ON sm.student_id = s.id
                WHERE s.id = %s
                GROUP BY s.id, s.name, s.prn, s.department
                """,
                (student_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            profile_id, name, department, prn, average_marks, subject_count = row
            return (
                profile_id,
                name,
                department,
                prn,
                average_marks,
                AcademicService.gpa_from_average(average_marks),
                AcademicService.grade_from_average(average_marks),
                subject_count,
            )
        finally:
            conn.close()

    @staticmethod
    def create_student(actor: dict, name: str, department: str, prn: str, username: str = "", password: str = "") -> tuple[str, str]:
        if not all([name, department, prn]):
            raise ValueError("Student name, department, and PRN are required.")

        conn = get_connection()
        try:
            conn.start_transaction()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM users WHERE role='student'")
            username = username.strip() or f"stud{cur.fetchone()[0] + 1}"
            password = password or username

            cur.execute(
                "INSERT INTO users(username, password_hash, role) VALUES (%s, %s, 'student')",
                (username, hash_password(password)),
            )
            user_id = cur.lastrowid
            cur.execute(
                "INSERT INTO students(name, department, prn, user_id, marks) VALUES (%s, %s, %s, %s, 0)",
                (name, department, prn, user_id),
            )
            conn.commit()
            log_audit(actor["id"], "CREATE_STUDENT", f"username={username} prn={prn} dept={department}")
            return username, password
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def update_student(actor: dict, student_id: int, name: str, department: str, prn: str) -> None:
        if not all([name, department, prn]):
            raise ValueError("Student name, department, and PRN are required.")

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE students SET name=%s, department=%s, prn=%s WHERE id=%s",
                (name, department, prn, student_id),
            )
            conn.commit()
            log_audit(actor["id"], "UPDATE_STUDENT", f"student_id={student_id} prn={prn}")
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def delete_student(actor: dict, student_id: int) -> None:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT user_id, prn FROM students WHERE id=%s", (student_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError("Student was not found.")
            user_id, prn = row
            cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
            conn.commit()
            log_audit(actor["id"], "DELETE_STUDENT", f"student_id={student_id} prn={prn}")
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def add_bonus_marks(actor: dict, department: str, bonus: float) -> int:
        if not department:
            raise ValueError("Enter a department first.")
        if bonus <= 0:
            raise ValueError("Bonus marks must be greater than 0.")

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE student_marks sm
                JOIN students s ON s.id = sm.student_id
                SET sm.marks = LEAST(sm.marks + %s, 100)
                WHERE s.department = %s
                """,
                (bonus, department),
            )
            affected = cur.rowcount
            conn.commit()
            log_audit(actor["id"], "ADD_BONUS_MARKS", f"department={department} bonus={bonus} affected={affected}")
            return affected
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def timestamped_export_path(path: str | Path) -> Path:
        export_path = Path(path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not re.search(r"\d{8}_\d{6}", export_path.stem):
            export_path = export_path.with_name(f"{export_path.stem}_{timestamp}{export_path.suffix or '.csv'}")
        return export_path

    @staticmethod
    def export_high_performers(path: str | Path) -> Path:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COALESCE(AVG(marks), 0) FROM student_marks")
            overall_average = float(cur.fetchone()[0] or 0)
        finally:
            conn.close()

        rows = [row for row in AcademicService.top_performers(1000) if float(row[4]) > overall_average]
        export_path = AcademicService.timestamped_export_path(path)
        with export_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Overall Average", overall_average])
            writer.writerow([])
            writer.writerow(["Rank", "Name", "PRN", "Department", "Average Marks", "GPA (Max 10)", "Grade", "Subjects"])
            writer.writerows(rows)
        return export_path
