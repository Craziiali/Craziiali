"""Drop text wherever the cursor is.

Copies to the clipboard and simulates the paste shortcut. The previous
clipboard contents are restored a moment later so we don't trample them.
"""
from __future__ import annotations

import sys
import time
import threading


def _clipboard_available() -> bool:
    try:
        import pyperclip  # noqa: F401
        return True
    except Exception:
        return False


def get_clipboard() -> str:
    try:
        import pyperclip
        return pyperclip.paste()
    except Exception:
        return ""


def set_clipboard(text: str) -> bool:
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        return False


def _send_paste() -> bool:
    try:
        import keyboard
        combo = "command+v" if sys.platform == "darwin" else "ctrl+v"
        keyboard.send(combo)
        return True
    except Exception:
        return False


def paste_text(text: str, *, restore_clipboard: bool = True, restore_delay: float = 0.6) -> bool:
    """Put `text` at the cursor. Returns True if the paste keystroke was sent."""
    if not text:
        return False

    previous = get_clipboard() if restore_clipboard else None
    if not set_clipboard(text):
        return False

    time.sleep(0.04)  # let the clipboard settle before pasting
    ok = _send_paste()

    if restore_clipboard and previous is not None:
        def _restore():
            time.sleep(restore_delay)
            set_clipboard(previous)
        threading.Thread(target=_restore, daemon=True).start()

    return ok


def can_autopaste() -> bool:
    try:
        import keyboard  # noqa: F401
        return _clipboard_available()
    except Exception:
        return False
