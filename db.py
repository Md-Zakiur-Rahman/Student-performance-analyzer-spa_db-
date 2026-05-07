import mysql.connector
import hashlib
import getpass
import sys
import os
from pathlib import Path

# ── GLOBAL DB CONFIG ──
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": None,       # set at first connection
    "database": "spa_db"
}


# ── INITIALIZE DB PASSWORD (only prompts once) ──
def init_db():
    if DB_CONFIG["password"] is None:
        DB_CONFIG["password"] = os.getenv("SPA_DB_PASSWORD")
    if DB_CONFIG["password"] is None:
        DB_CONFIG["password"] = getpass.getpass("Enter MySQL root password: ")


def set_db_password(password: str) -> None:
    DB_CONFIG["password"] = password


class AuthService:
    @staticmethod
    def authenticate(identifier: str, password: str, mysql_password: str) -> dict | None:
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


# ── CONNECTION ──
def get_connection():
    init_db()
    return mysql.connector.connect(**DB_CONFIG)


# ── PASSWORD HASH (SHA-256) ──
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ── AUDIT LOG (safe wrapper — must never crash main app) ──
def log_audit(user_id, action: str, details: str = ""):
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(
            "INSERT INTO audit_log(user_id, action, details) VALUES (%s, %s, %s)",
            (user_id, action, details)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        # Print to stderr only — must never propagate to main app
        print(f"[audit_log error] {e}", file=sys.stderr)


# ── TEST CONNECTION ──
def test_connection():
    try:
        conn = get_connection()
        print("✅ Database connection successful")
        conn.close()
    except Exception as e:
        print("❌ Connection failed:", e)


def ensure_db_setup(sql_path: str | None = None) -> None:
    """Ensure the database and tables exist by running the PRN_setup.sql script.

    Uses the configured `DB_CONFIG` credentials (prompts if not set). Connects
    without a database to run `CREATE DATABASE` and table creation statements.
    """
    init_db()

    cfg = DB_CONFIG.copy()
    cfg.pop("database", None)

    if sql_path is None:
        sql_path = Path(__file__).resolve().parent / "PRN_setup.sql"
    else:
        sql_path = Path(sql_path)

    if not sql_path.exists():
        return

    try:
        conn = mysql.connector.connect(**cfg)
        cur = conn.cursor()
        sql = sql_path.read_text(encoding="utf-8")
        for result in cur.execute(sql, multi=True):
            pass
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        raise RuntimeError(f"Failed to ensure DB setup: {e}") from e
