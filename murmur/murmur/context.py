"""Best-effort context about what the user is doing right now.

Used for (a) auto-switching modes by active app and (b) giving the rewriter
optional context. Everything degrades gracefully to empty strings.
"""
from __future__ import annotations

import sys
import time

from . import paste


def active_window() -> dict[str, str]:
    """Return {'app': ..., 'title': ...} for the foreground window, best-effort."""
    try:
        if sys.platform.startswith("win"):
            return _active_windows()
        if sys.platform == "darwin":
            return _active_macos()
        return _active_linux()
    except Exception:
        return {"app": "", "title": ""}


def _active_windows() -> dict[str, str]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    title = buf.value

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    app = ""
    try:
        import psutil
        app = psutil.Process(pid.value).name()
    except Exception:
        app = title
    return {"app": app, "title": title}


def _active_macos() -> dict[str, str]:
    from subprocess import check_output
    script = 'tell application "System Events" to get name of first application process whose frontmost is true'
    app = check_output(["osascript", "-e", script], timeout=1).decode().strip()
    return {"app": app, "title": app}


def _active_linux() -> dict[str, str]:
    from subprocess import check_output
    try:
        title = check_output(["xdotool", "getactivewindow", "getwindowname"], timeout=1).decode().strip()
        return {"app": title, "title": title}
    except Exception:
        return {"app": "", "title": ""}


def gather(mode, *, want_selection: bool = False) -> dict[str, str]:
    """Collect context a mode is allowed to read."""
    ctx: dict[str, str] = {}
    if getattr(mode, "use_active_app", False):
        ctx.update(active_window())
    if getattr(mode, "use_clipboard", False):
        ctx["clipboard"] = paste.get_clipboard()
    if getattr(mode, "use_selection", False) and want_selection:
        ctx["selection"] = _capture_selection()
    return ctx


def _capture_selection() -> str:
    """Grab the currently selected text by copying it, then restoring clipboard."""
    try:
        import keyboard
        previous = paste.get_clipboard()
        paste.set_clipboard("")
        time.sleep(0.03)
        keyboard.send("command+c" if sys.platform == "darwin" else "ctrl+c")
        time.sleep(0.12)
        sel = paste.get_clipboard()
        paste.set_clipboard(previous)
        return sel if sel else ""
    except Exception:
        return ""
