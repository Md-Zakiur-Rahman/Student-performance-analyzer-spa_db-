from db import get_connection, log_audit


class FacultyService:
    @staticmethod
    def assigned_subjects(faculty_id: int) -> list[str]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT subject_name FROM faculty_subjects WHERE faculty_id=%s ORDER BY subject_name",
                (faculty_id,),
            )
            return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def find_student_by_prn(prn: str) -> tuple | None:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, name, department, prn FROM students WHERE prn=%s", (prn,))
            return cur.fetchone()
        finally:
            conn.close()

    @staticmethod
    def marks(student_id: int) -> list[tuple]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT subject, marks FROM student_marks WHERE student_id=%s ORDER BY subject", (student_id,))
            return cur.fetchall()
        finally:
            conn.close()

    @staticmethod
    def subject_roster(faculty_id: int, subject: str) -> list[tuple]:
        if subject not in FacultyService.assigned_subjects(faculty_id):
            raise PermissionError("Faculty is not assigned to this subject.")

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT s.id, s.name, s.prn, sm.marks
                FROM students s
                LEFT JOIN student_marks sm
                       ON sm.student_id = s.id AND sm.subject = %s
                ORDER BY s.name
                """,
                (subject,),
            )
            return cur.fetchall()
        finally:
            conn.close()

    @staticmethod
    def upsert_mark(faculty_user: dict, student_id: int, subject: str, marks: float) -> None:
        if subject not in FacultyService.assigned_subjects(faculty_user["id"]):
            raise PermissionError("Faculty is not assigned to this subject.")
        if not 0 <= marks <= 100:
            raise ValueError("Marks must be between 0 and 100.")

        conn = get_connection()
        try:
            conn.start_transaction()
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM student_marks WHERE student_id=%s AND subject=%s",
                (student_id, subject),
            )
            exists = cur.fetchone()
            if exists:
                cur.execute(
                    "UPDATE student_marks SET marks=%s WHERE student_id=%s AND subject=%s",
                    (marks, student_id, subject),
                )
                action = "UPDATE_MARKS"
            else:
                cur.execute(
                    "INSERT INTO student_marks(student_id, subject, marks) VALUES (%s, %s, %s)",
                    (student_id, subject, marks),
                )
                action = "INSERT_MARKS"
            conn.commit()
            log_audit(faculty_user["id"], action, f"student_id={student_id} subject={subject} marks={marks}")
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def bulk_update_marks(faculty_user: dict, subject: str, updates: list[tuple[int, float]]) -> tuple[int, int]:
        if subject not in FacultyService.assigned_subjects(faculty_user["id"]):
            raise PermissionError("Faculty is not assigned to this subject.")

        conn = get_connection()
        try:
            conn.start_transaction()
            cur = conn.cursor()
            inserted = 0
            updated = 0

            for student_id, marks in updates:
                if not 0 <= marks <= 100:
                    raise ValueError("Marks must be between 0 and 100.")
                cur.execute(
                    "SELECT id FROM student_marks WHERE student_id=%s AND subject=%s",
                    (student_id, subject),
                )
                exists = cur.fetchone()
                if exists:
                    cur.execute(
                        "UPDATE student_marks SET marks=%s WHERE student_id=%s AND subject=%s",
                        (marks, student_id, subject),
                    )
                    updated += 1
                else:
                    cur.execute(
                        "INSERT INTO student_marks(student_id, subject, marks) VALUES (%s, %s, %s)",
                        (student_id, subject, marks),
                    )
                    inserted += 1

            conn.commit()
            log_audit(
                faculty_user["id"],
                "BULK_UPDATE_MARKS",
                f"subject={subject} updated={updated} inserted={inserted}",
            )
            return updated, inserted
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
