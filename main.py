import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from controllers.login_controller import LoginController


BASE_DIR = Path(__file__).resolve().parent


def load_stylesheet(app: QApplication) -> None:
    qss_path = BASE_DIR / "ui" / "cyberpunk.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Student Performance Analyzer")
    app.setQuitOnLastWindowClosed(True)
    load_stylesheet(app)

    login = LoginController()
    login.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
