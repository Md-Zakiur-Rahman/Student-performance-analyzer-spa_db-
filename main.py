import sys
import os
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QInputDialog, QLineEdit, QMessageBox

from controllers.login_controller import LoginController
from db import ensure_db_setup


BASE_DIR = Path(__file__).resolve().parent


def load_stylesheet(app: QApplication) -> None:
    qss_path = BASE_DIR / "ui" / "cyberpunk.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))


def main() -> int:

    # Create the QApplication early so we can prompt for the MySQL root
    # password in a GUI (needed when running a windowed exe).
    app = QApplication(sys.argv)
    app.setApplicationName("Student Performance Analyzer")
    app.setQuitOnLastWindowClosed(True)

    # If no password provided via env, ask via GUI dialog so a windowed exe can obtain it.
    if os.getenv("SPA_DB_PASSWORD") is None:
        pwd, ok = QInputDialog.getText(None, "MySQL Password",
                                       "Enter MySQL root password to initialize the database:",
                                       QLineEdit.EchoMode.Password)
        if ok and pwd:
            os.environ["SPA_DB_PASSWORD"] = pwd
        else:
            QMessageBox.critical(None, "Database Setup Aborted",
                                 "No MySQL password provided. Set SPA_DB_PASSWORD or run the app from a console.")
            return 1

    try:
        ensure_db_setup()
    except Exception as e:
        QMessageBox.critical(None, "Database Error", f"Error during DB setup: {e}")
        return 1

    load_stylesheet(app)

    login = LoginController()
    login.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
