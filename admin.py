from db import get_connection, hash_password, log_audit


class AdminService:
    @staticmethod
    def users() -> list[tuple]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT username, role, is_active, created_at
                FROM users
                ORDER BY role, username
                """
            )
            return cur.fetchall()
        finally:
            conn.close()

    @staticmethod
    def subjects() -> list[str]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT name FROM subjects ORDER BY name")
            return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def audit_log(limit: int = 50) -> list[tuple]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT COALESCE(u.username, 'SYSTEM'), a.action, a.details, a.timestamp
                FROM audit_log a
                LEFT JOIN users u ON u.id = a.user_id
                ORDER BY a.timestamp DESC
                LIMIT %s
                """,
                (limit,),
            )
            return cur.fetchall()
        finally:
            conn.close()

    @staticmethod
    def add_subject(admin_user: dict, name: str) -> None:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO subjects(name) VALUES (%s)", (name,))
            conn.commit()
            log_audit(admin_user["id"], "ADD_SUBJECT", f"subject={name}")
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def create_user(
        admin_user: dict,
        role: str,
        username: str,
        password: str,
        name: str = "",
        department: str = "",
        prn: str = "",
        subjects: list[str] | None = None,
    ) -> tuple[str, str]:
        if role not in {"admin", "faculty", "student"}:
            raise ValueError("Role must be admin, faculty, or student.")

        conn = get_connection()
        try:
            conn.start_transaction()
            cur = conn.cursor()

            if role == "student":
                if not all([name, department, prn]):
                    raise ValueError("Student name, department, and PRN are required.")
                cur.execute("SELECT COUNT(*) FROM users WHERE role='student'")
                username = username or f"stud{cur.fetchone()[0] + 1}"
                password = password or username

            if not all([username, password, role]):
                raise ValueError("Username, password, and role are required.")
            if role == "faculty" and not subjects:
                raise ValueError("Faculty users must be assigned at least one subject.")

            cur.execute(
                "INSERT INTO users(username, password_hash, role) VALUES (%s, %s, %s)",
                (username, hash_password(password), role),
            )
            user_id = cur.lastrowid

            if role == "student":
                cur.execute(
                    """
                    INSERT INTO students(name, department, prn, user_id, marks)
                    VALUES (%s, %s, %s, %s, 0)
                    """,
                    (name, department, prn, user_id),
                )
                action = "CREATE_STUDENT"
                detail = f"username={username} prn={prn} dept={department}"
            elif role == "faculty":
                for subject in subjects or []:
                    cur.execute(
                        "INSERT INTO faculty_subjects(faculty_id, subject_name) VALUES (%s, %s)",
                        (user_id, subject),
                    )
                action = "CREATE_FACULTY"
                detail = f"username={username} subjects={subjects or []}"
            else:
                action = "CREATE_ADMIN"
                detail = f"username={username}"

            conn.commit()
            log_audit(admin_user["id"], action, detail)
            return username, password
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def toggle_user(admin_user: dict, username: str) -> bool:
        if username == admin_user["username"]:
            raise ValueError("You cannot disable your own account.")

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT is_active FROM users WHERE username=%s", (username,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"User '{username}' was not found.")

            new_status = not bool(row[0])
            cur.execute("UPDATE users SET is_active=%s WHERE username=%s", (new_status, username))
            conn.commit()
            log_audit(admin_user["id"], "TOGGLE_USER", f"username={username} is_active={new_status}")
            return new_status
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
