"""Where Murmur keeps its files, resolved per-platform.

Windows : %APPDATA%\\Murmur
macOS   : ~/Library/Application Support/Murmur
Linux   : $XDG_CONFIG_HOME/murmur  (or ~/.config/murmur)
"""
from __future__ import annotations

import os
import sys
import pathlib


def data_dir() -> pathlib.Path:
    """Return (creating if needed) the per-user directory for Murmur's data."""
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        path = pathlib.Path(base) / "Murmur"
    elif sys.platform == "darwin":
        path = pathlib.Path.home() / "Library" / "Application Support" / "Murmur"
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
        path = pathlib.Path(base) / "murmur"
    path.mkdir(parents=True, exist_ok=True)
    return path


def models_dir() -> pathlib.Path:
    """Directory where local Whisper models are cached."""
    path = data_dir() / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ui_dir() -> pathlib.Path:
    """Directory holding the bundled HTML/CSS/JS UI."""
    return pathlib.Path(__file__).resolve().parent / "ui"


def config_file() -> pathlib.Path:
    return data_dir() / "settings.json"


def modes_file() -> pathlib.Path:
    return data_dir() / "modes.json"


def history_db() -> pathlib.Path:
    return data_dir() / "history.db"
