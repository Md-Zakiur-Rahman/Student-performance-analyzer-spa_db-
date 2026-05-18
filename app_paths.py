import sys
from pathlib import Path


def resource_path(*parts: str) -> Path:
    """Return a project resource path in source runs and PyInstaller builds."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base.joinpath(*parts)
