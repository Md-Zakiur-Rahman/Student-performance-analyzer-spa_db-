import hashlib
import os
import sys
from pathlib import Path

import mysql.connector

from app_paths import resource_path


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": None,
    "database": "spa_db",
    "use_pure": True,
    "consume_results": True,
}


def init_db() -> None:
    if DB_CONFIG["password"] is None:
        DB_CONFIG["password"] = os.getenv("SPA_DB_PASSWORD")


def set_db_password(password: str) -> None:
    DB_CONFIG["password"] = password


def get_connection():
    init_db()
    return mysql.connector.connect(**DB_CONFIG)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


class AuthService:
    @staticmethod
    def authenticate(identifier: str, password: str, mysql_password: str | None = None) -> dict | None:
        if mysql_password:
            set_db_password(mysql_password)

        password_hash = hash_password(password)
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                SELECT *
                FROM users
                WHERE username = %s
                  AND password_hash = %s
                  AND is_active = TRUE
                """,
                (identifier, password_hash),
            )
            user = cur.fetchone()

            if not user:
                cur.execute(
                    """
                    SELECT u.*
                    FROM users u
                    JOIN students s ON s.user_id = u.id
                    WHERE s.prn = %s
                      AND u.password_hash = %s
                      AND u.is_active = TRUE
                    """,
                    (identifier, password_hash),
                )
                user = cur.fetchone()

            if not user:
                log_audit(None, "LOGIN_FAILED", f"identifier={identifier}")
                return None

            cur.execute("SELECT id FROM students WHERE user_id = %s", (user["id"],))
            student = cur.fetchone()
            user["student_id"] = student["id"] if student else None

            log_audit(user["id"], "LOGIN_SUCCESS", f"identifier={identifier} role={user['role']}")
            return user
        finally:
            conn.close()


def log_audit(user_id, action: str, details: str = "") -> None:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO audit_log(user_id, action, details) VALUES (%s, %s, %s)",
            (user_id, action, details),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as exc:
        print(f"[audit_log error] {exc}", file=sys.stderr)


def test_connection() -> None:
    try:
        conn = get_connection()
        print("Database connection successful")
        conn.close()
    except Exception as exc:
        print("Connection failed:", exc)


def split_sql_statements(sql: str) -> list[str]:
    statements = []
    current = []
    quote = None
    in_line_comment = False
    in_block_comment = False
    index = 0

    while index < len(sql):
        char = sql[index]
        next_char = sql[index + 1] if index + 1 < len(sql) else ""

        if in_line_comment:
            current.append(char)
            if char in "\r\n":
                in_line_comment = False
            index += 1
            continue

        if in_block_comment:
            current.append(char)
            if char == "*" and next_char == "/":
                current.append(next_char)
                in_block_comment = False
                index += 2
            else:
                index += 1
            continue

        if quote:
            current.append(char)
            if char == "\\" and next_char:
                current.append(next_char)
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue

        if char in {"'", '"', "`"}:
            quote = char
            current.append(char)
            index += 1
            continue

        if char == "-" and next_char == "-":
            previous = sql[index - 1] if index > 0 else "\n"
            following = sql[index + 2] if index + 2 < len(sql) else "\n"
            if previous in "\r\n\t " and following in "\r\n\t ":
                in_line_comment = True
                current.extend([char, next_char])
                index += 2
                continue

        if char == "#":
            in_line_comment = True
            current.append(char)
            index += 1
            continue

        if char == "/" and next_char == "*":
            in_block_comment = True
            current.extend([char, next_char])
            index += 2
            continue

        if char == ";":
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
            index += 1
            continue

        current.append(char)
        index += 1

    statement = "".join(current).strip()
    if statement:
        statements.append(statement)

    return statements


def ensure_db_setup(sql_path: str | Path | None = None) -> None:
    init_db()

    cfg = DB_CONFIG.copy()
    cfg.pop("database", None)

    if sql_path is None:
        sql_file = resource_path("PRN_setup.sql")
    else:
        sql_file = Path(sql_path)
        if not sql_file.is_absolute():
            sql_file = resource_path(str(sql_file))

    if not sql_file.exists():
        raise FileNotFoundError(f"Database setup script not found: {sql_file}")

    try:
        conn = mysql.connector.connect(**cfg)
        cur = conn.cursor()
        sql = sql_file.read_text(encoding="utf-8")
        for statement in split_sql_statements(sql):
            cur.execute(statement)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as exc:
        raise RuntimeError(f"Failed to ensure DB setup: {exc}") from exc


def remove_demo_seed_data() -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                setting_key VARCHAR(100) PRIMARY KEY,
                setting_value VARCHAR(255) NOT NULL,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB
              DEFAULT CHARSET=utf8mb4
              COLLATE=utf8mb4_0900_ai_ci
            """
        )
        cur.execute("SELECT setting_value FROM app_settings WHERE setting_key='initial_academic_cleanup_done'")
        if cur.fetchone():
            cur.close()
            conn.close()
            return

        cur.execute(
            """
            DELETE sm
            FROM student_marks sm
            JOIN students s ON s.id = sm.student_id
            WHERE s.prn IN ('PRN001', 'PRN002')
            """
        )
        cur.execute("DELETE FROM student_marks")
        cur.execute("DELETE FROM students")
        cur.execute("DELETE FROM faculty_subjects")
        cur.execute("DELETE FROM subjects")
        cur.execute("DELETE FROM users WHERE role IN ('faculty', 'student')")
        cur.execute(
            """
            INSERT INTO app_settings(setting_key, setting_value)
            VALUES ('demo_seed_cleanup_done', '1')
            ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)
            """
        )
        cur.execute(
            """
            INSERT INTO app_settings(setting_key, setting_value)
            VALUES ('initial_academic_cleanup_done', '1')
            ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)
            """
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as exc:
        conn.rollback()
        raise RuntimeError(f"Failed to remove demo seed data: {exc}") from exc


def db_exists(password: str | None = None, timeout: int = 5) -> bool:
    cfg = DB_CONFIG.copy()
    cfg["password"] = password if password is not None else os.getenv("SPA_DB_PASSWORD", "")

    try:
        conn = mysql.connector.connect(**cfg, connection_timeout=timeout)
        conn.close()
        return True
    except mysql.connector.Error:
        return False
    except Exception:
        return False
