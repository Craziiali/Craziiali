"""Global hold-to-talk hotkey.

The press/release state machine (`HoldDetector`) is pure and unit-tested.
`HotkeyListener` wires it to OS-level keyboard events via the `keyboard` lib.
"""
from __future__ import annotations

from typing import Callable

MODIFIERS = {"alt", "ctrl", "control", "shift", "cmd", "win", "windows", "super"}
_ALIASES = {"control": "ctrl", "windows": "win", "cmd": "win", "super": "win",
            "option": "alt", "spacebar": "space", "esc": "escape"}


def parse_combo(combo: str) -> tuple[frozenset[str], str]:
    """'alt+space' -> (frozenset{'alt'}, 'space'). Last non-modifier is the trigger."""
    parts = [_ALIASES.get(p.strip().lower(), p.strip().lower())
             for p in combo.split("+") if p.strip()]
    mods, trigger = set(), ""
    for p in parts:
        if p in MODIFIERS:
            mods.add(_ALIASES.get(p, p))
        else:
            trigger = p
    return frozenset(mods), trigger


class HoldDetector:
    """Feeds key down/up events; fires on_start when the combo engages and
    on_stop when it releases. Order-independent for modifiers vs. trigger."""

    def __init__(self, combo: str, on_start: Callable[[], None], on_stop: Callable[[], None]):
        self.mods, self.trigger = parse_combo(combo)
        self.on_start = on_start
        self.on_stop = on_stop
        self._pressed: set[str] = set()
        self._active = False

    def feed(self, name: str, is_down: bool) -> None:
        name = _ALIASES.get(name.lower(), name.lower())
        if is_down:
            self._pressed.add(name)
            if not self._active and self.trigger in self._pressed and self.mods <= self._pressed:
                self._active = True
                self.on_start()
        else:
            self._pressed.discard(name)
            if self._active and (name == self.trigger or name in self.mods):
                self._active = False
                self.on_stop()

    @property
    def active(self) -> bool:
        return self._active


def available() -> bool:
    try:
        import keyboard  # noqa: F401
        return True
    except Exception:
        return False


class HotkeyListener:
    """Listens system-wide and drives a HoldDetector. Windows-friendly."""

    def __init__(self, combo: str, on_start, on_stop):
        self._detector = HoldDetector(combo, on_start, on_stop)
        self._hook = None

    def start(self) -> bool:
        if not available():
            return False
        import keyboard
        self._hook = keyboard.hook(self._on_event)
        return True

    def stop(self) -> None:
        if self._hook is not None:
            import keyboard
            keyboard.unhook(self._hook)
            self._hook = None

    def rebind(self, combo: str) -> None:
        on_start, on_stop = self._detector.on_start, self._detector.on_stop
        self._detector = HoldDetector(combo, on_start, on_stop)

    def _on_event(self, event) -> None:  # noqa: ANN001
        name = getattr(event, "name", None)
        if not name:
            return
        self._detector.feed(name, getattr(event, "event_type", "down") == "down")
