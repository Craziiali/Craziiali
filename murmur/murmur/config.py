"""User settings: load, validate, persist, observe.

Settings live in a single JSON file. Unknown keys are ignored on load and
missing keys fall back to defaults, so the file is always forward/backward
compatible across versions.
"""
from __future__ import annotations

import json
import threading
from typing import Any, Callable

from . import paths

DEFAULTS: dict[str, Any] = {
    "theme": "dark",            # auto | light | dark
    "engine": "auto",           # auto | local | cloud
    "localModel": "base",       # tiny | base | small | medium | large-v3
    "language": "auto",         # auto | en | es | ...
    "hotkey": "alt+space",      # hold-to-talk combo (keyboard lib syntax)
    "launchAtLogin": True,
    "playSounds": True,
    "autoPaste": True,
    "trimFillers": True,
    "openaiKey": "",
    "anthropicKey": "",
    "microphone": "default",    # "default" or a device name/index
    "activeMode": "voice",
}

# Keys that are secret — never logged or returned to the UI in full.
SECRET_KEYS = {"openaiKey", "anthropicKey"}

_VALID = {
    "theme": {"auto", "light", "dark"},
    "engine": {"auto", "local", "cloud"},
    "localModel": {"tiny", "base", "small", "medium", "large-v3"},
}


class Config:
    """Thread-safe settings store backed by a JSON file."""

    def __init__(self, path=None):
        self._path = path or paths.config_file()
        self._lock = threading.RLock()
        self._data: dict[str, Any] = dict(DEFAULTS)
        self._subs: list[Callable[[str, Any], None]] = []
        self.load()

    # -------------------------------------------------- io
    def load(self) -> None:
        with self._lock:
            self._data = dict(DEFAULTS)
            try:
                raw = json.loads(self._path.read_text("utf-8"))
                for k, v in raw.items():
                    if k in DEFAULTS:
                        self._data[k] = v
            except (FileNotFoundError, json.JSONDecodeError, OSError):
                pass

    def save(self) -> None:
        with self._lock:
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._data, indent=2), "utf-8")
            tmp.replace(self._path)

    # -------------------------------------------------- access
    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value: Any) -> Any:
        """Set + validate + persist a single key. Returns the stored value."""
        if key not in DEFAULTS:
            return None
        value = self._coerce(key, value)
        with self._lock:
            self._data[key] = value
            self.save()
        for cb in list(self._subs):
            try:
                cb(key, value)
            except Exception:
                pass
        return value

    def all(self, redact: bool = False) -> dict[str, Any]:
        with self._lock:
            data = dict(self._data)
        if redact:
            for k in SECRET_KEYS:
                data[k] = bool(data.get(k))  # expose only whether a key is set
        return data

    def subscribe(self, cb: Callable[[str, Any], None]) -> None:
        self._subs.append(cb)

    # -------------------------------------------------- helpers
    @staticmethod
    def _coerce(key: str, value: Any) -> Any:
        default = DEFAULTS[key]
        if isinstance(default, bool):
            return bool(value) if not isinstance(value, str) else value.lower() in ("1", "true", "yes", "on")
        if isinstance(default, str):
            value = str(value)
            if key in _VALID and value not in _VALID[key]:
                return default
            return value
        return value
