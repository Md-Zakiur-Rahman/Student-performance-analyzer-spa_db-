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
    def user(username: str) -> tuple | None:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, username, role, is_active FROM users WHERE username=%s", (username,))
            return cur.fetchone()
        finally:
            conn.close()

    @staticmethod
    def faculty_subjects(username: str) -> list[str]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT fs.subject_name
                FROM faculty_subjects fs
                JOIN users u ON u.id = fs.faculty_id
                WHERE u.username = %s
                ORDER BY fs.subject_name
                """,
                (username,),
            )
            return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def student_profile(username: str) -> tuple | None:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT s.name, s.department, s.prn
                FROM students s
                JOIN users u ON u.id = s.user_id
                WHERE u.username = %s
                """,
                (username,),
            )
            return cur.fetchone()
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
    def update_subject(admin_user: dict, old_name: str, new_name: str) -> None:
        if not new_name:
            raise ValueError("Subject name is required.")

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE subjects SET name=%s WHERE name=%s", (new_name, old_name))
            if cur.rowcount == 0:
                raise ValueError(f"Subject '{old_name}' was not found.")
            conn.commit()
            log_audit(admin_user["id"], "UPDATE_SUBJECT", f"{old_name} -> {new_name}")
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def delete_subject(admin_user: dict, name: str) -> None:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM subjects WHERE name=%s", (name,))
            if cur.rowcount == 0:
                raise ValueError(f"Subject '{name}' was not found.")
            conn.commit()
            log_audit(admin_user["id"], "DELETE_SUBJECT", f"subject={name}")
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
            cur = conn.cursor(buffered=True)

            if role == "student":
                if not all([name, department, prn]):
                    raise ValueError("Student name, department, and PRN are required.")
                cur.execute("SELECT COUNT(*) FROM users WHERE role='student'")
                student_count = cur.fetchone()[0]
                username = username or f"stud{student_count + 1}"
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
            cur.close()
            conn.close()
            log_audit(admin_user["id"], action, detail)
            return username, password
        except Exception:
            conn.rollback()
            raise
        finally:
            if conn.is_connected():
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

    @staticmethod
    def update_user(
        admin_user: dict,
        old_username: str,
        new_username: str,
        new_password: str = "",
        subjects: list[str] | None = None,
        student_profile: tuple[str, str, str] | None = None,
    ) -> None:
        if not new_username:
            raise ValueError("Username is required.")

        conn = get_connection()
        try:
            conn.start_transaction()
            cur = conn.cursor()
            cur.execute("SELECT id, role FROM users WHERE username=%s", (old_username,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"User '{old_username}' was not found.")
            user_id, role = row

            if new_password:
                cur.execute(
                    "UPDATE users SET username=%s, password_hash=%s WHERE id=%s",
                    (new_username, hash_password(new_password), user_id),
                )
            else:
                cur.execute("UPDATE users SET username=%s WHERE id=%s", (new_username, user_id))

            if role == "faculty" and subjects is not None:
                if not subjects:
                    raise ValueError("Faculty users must be assigned at least one subject.")
                cur.execute("DELETE FROM faculty_subjects WHERE faculty_id=%s", (user_id,))
                for subject in subjects:
                    cur.execute(
                        "INSERT INTO faculty_subjects(faculty_id, subject_name) VALUES (%s, %s)",
                        (user_id, subject),
                    )

            if role == "student" and student_profile is not None:
                name, department, prn = student_profile
                if not all([name, department, prn]):
                    raise ValueError("Student name, department, and PRN are required.")
                cur.execute(
                    "UPDATE students SET name=%s, department=%s, prn=%s WHERE user_id=%s",
                    (name, department, prn, user_id),
                )

            conn.commit()
            log_audit(admin_user["id"], "UPDATE_USER", f"{old_username} -> {new_username}")
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def delete_user(admin_user: dict, username: str) -> None:
        if username == admin_user["username"]:
            raise ValueError("You cannot delete your own account.")

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM users WHERE username=%s", (username,))
            if cur.rowcount == 0:
                raise ValueError(f"User '{username}' was not found.")
            conn.commit()
            log_audit(admin_user["id"], "DELETE_USER", f"username={username}")
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def create_mysql_application_users(admin_user: dict) -> None:
        conn = get_connection()
        try:
            cur = conn.cursor()
            statements = [
                "CREATE USER IF NOT EXISTS 'spa_admin'@'localhost' IDENTIFIED BY 'admin123'",
                "CREATE USER IF NOT EXISTS 'spa_faculty'@'localhost' IDENTIFIED BY 'faculty123'",
                "CREATE USER IF NOT EXISTS 'spa_student'@'localhost' IDENTIFIED BY 'student123'",
                "GRANT ALL PRIVILEGES ON spa_db.* TO 'spa_admin'@'localhost'",
                "GRANT SELECT, INSERT, UPDATE ON spa_db.* TO 'spa_faculty'@'localhost'",
                "GRANT SELECT ON spa_db.* TO 'spa_student'@'localhost'",
                "FLUSH PRIVILEGES",
            ]
            for statement in statements:
                cur.execute(statement)
            conn.commit()
            log_audit(admin_user["id"], "CREATE_MYSQL_APP_USERS", "spa_admin/spa_faculty/spa_student")
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
