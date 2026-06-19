"""The Murmur controller + the bridge the UI talks to.

`Controller` owns the dictation pipeline and the background services.
`Api` is the thin, JSON-friendly surface exposed to the web UI via pywebview.
"""
from __future__ import annotations

import json
import threading

from . import audio, paste, context as ctx
from .config import Config
from .modes import Mode, ModeStore
from .history import History
from .hotkeys import HotkeyListener
from .transcribe.engine import Transcriber
from .transcribe.base import TranscriptionError
from .rewrite.llm import Rewriter


def mode_ui_dict(m: Mode) -> dict:
    """Shape a Mode for the Modes grid in the UI."""
    if m.engine == "cloud":
        trans = "Cloud · whisper"
    else:
        trans = f"Local · {m.trans_model}"
    llm = {"openai": "GPT", "anthropic": "Claude"}.get(m.llm_provider, "—")
    tags = []
    if m.engine == "local":
        tags.append("Offline")
    if not m.rewrites:
        tags.append("Verbatim")
    if m.tone:
        tags.append(m.tone)
    if m.auto_apps:
        tags.append(f"Auto: {m.auto_apps[0].title()}")
    return {
        "id": m.id, "name": m.name, "glyph": m.glyph,
        "key": (m.hotkey or "").title() or "—",
        "desc": m.desc, "transModel": trans, "llm": llm, "tags": tags,
    }


class Controller:
    def __init__(self):
        self.config = Config()
        self.modes = ModeStore()
        self.history = History()
        self.transcriber = Transcriber(self.config)
        self.rewriter = Rewriter(self.config)

        self.main_window = None
        self.pill_window = None
        self.recorder: audio.Recorder | None = None
        self.listener: HotkeyListener | None = None
        self._busy = threading.Lock()
        self._active_mode_id = self.config.get("activeMode", "voice")

    # ------------------------------------------------------------- wiring
    def attach_windows(self, main_window, pill_window) -> None:
        self.main_window = main_window
        self.pill_window = pill_window

    def start_services(self) -> None:
        combo = self.config.get("hotkey", "alt+space")
        self.listener = HotkeyListener(combo, self._on_press, self._on_release)
        if not self.listener.start():
            print("[murmur] global hotkey unavailable (install `keyboard`).")
        if not audio.available():
            print("[murmur] microphone capture unavailable (install `sounddevice`).")

    def shutdown(self) -> None:
        if self.listener:
            self.listener.stop()

    # ---------------------------------------------------------- pipeline
    def _current_mode(self) -> Mode:
        return self.modes.get(self._active_mode_id) or self.modes.list()[0]

    def _on_press(self) -> None:
        """Hotkey engaged — begin recording immediately (cheap, on hook thread)."""
        if self.recorder and self.recorder.recording:
            return

        # Auto-switch mode based on the active app, if a rule matches.
        try:
            window = ctx.active_window()
            auto = self.modes.match_auto(window)
            if auto:
                self._active_mode_id = auto.id
        except Exception:
            pass

        mode = self._current_mode()
        self.recorder = audio.Recorder(
            on_level=self._on_level,
            device=self.config.get("microphone", "default"),
        )
        self._pill_show()
        self._pill("setState", "listening")
        self._pill("setMode", mode.name, self.config.get("hotkey", "").title())
        self.recorder.start()

    def _on_release(self) -> None:
        """Hotkey released — hand the heavy work to a worker thread."""
        if not self.recorder or not self.recorder.recording:
            return
        threading.Thread(target=self._finish, daemon=True).start()

    def _finish(self) -> None:
        if not self._busy.acquire(blocking=False):
            return
        try:
            rec = self.recorder
            duration = rec.duration() if rec else 0.0
            wav = rec.stop() if rec else None
            mode = self._current_mode()

            if not wav:
                self._pill("setState", "idle")
                self._pill_hide(delay=600)
                return

            self._pill("setState", "transcribing")
            try:
                result = self.transcriber.transcribe(wav, mode)
            except TranscriptionError as e:
                self._toast(str(e))
                self._pill("setState", "idle")
                self._pill_hide(delay=900)
                return

            raw = result.text
            text = raw
            if mode.rewrites:
                self._pill("setState", "polishing")
                want_sel = mode.use_selection
                context = ctx.gather(mode, want_selection=want_sel)
                text = self.rewriter.rewrite(mode, raw, context) or raw

            # Drop it at the cursor.
            if self.config.get("autoPaste", True) and text:
                paste.paste_text(text)
            else:
                paste.set_clipboard(text)

            self.history.add(mode_id=mode.id, mode_name=mode.name, glyph=mode.glyph,
                             raw=raw, text=text, duration=duration)

            self._pill("setState", "done")
            self._pill_hide(delay=900)
            self._push_main("setLastText", text)
            self._main_eval("window.murmur && window.murmur.refreshHistory()")
        finally:
            self._busy.release()

    def _on_level(self, level: float) -> None:
        self._pill("setAmp", level)

    # --------------------------------------------------------- UI bridge
    def _pill(self, method: str, *args) -> None:
        if not self.pill_window:
            return
        argstr = ", ".join(json.dumps(a) for a in args)
        self._eval(self.pill_window, f"window.pill && window.pill.{method}({argstr})")

    def _pill_show(self) -> None:
        if self.pill_window:
            try:
                self.pill_window.show()
            except Exception:
                pass

    def _pill_hide(self, delay: int = 0) -> None:
        def _do():
            if self.pill_window:
                try:
                    self.pill_window.hide()
                except Exception:
                    pass
        if delay:
            threading.Timer(delay / 1000.0, _do).start()
        else:
            _do()

    def _push_main(self, method: str, *args) -> None:
        argstr = ", ".join(json.dumps(a) for a in args)
        self._main_eval(f"window.murmur && window.murmur.{method}({argstr})")

    def _main_eval(self, expr: str) -> None:
        if self.main_window:
            self._eval(self.main_window, expr)

    def _toast(self, msg: str) -> None:
        self._main_eval(f"window.murmur && window.murmur.toast && window.murmur.toast({json.dumps(msg)})")

    @staticmethod
    def _eval(window, expr: str) -> None:
        try:
            window.evaluate_js(expr)
        except Exception:
            pass


class Api:
    """JSON-friendly surface exposed to the web UI."""

    def __init__(self, controller: Controller):
        self.c = controller

    # ---- reads ----
    def get_state(self) -> dict:
        c = self.c
        caps = c.transcriber.capabilities(check_online=False)
        engine_mode = "local" if (c.config.get("engine") in ("auto", "local") and caps.local_available) else "cloud"
        mics = audio.list_microphones()
        mode = c._current_mode()
        hist = c.history.list(limit=1)
        return {
            "engine": {"mode": engine_mode, "model": c.config.get("localModel"),
                       "online": True},
            "mic": {"ready": audio.available(),
                    "name": (mics[0]["name"] if mics else "No microphone")},
            "activeMode": mode.id,
            "theme": c.config.get("theme"),
            "hotkey": c.config.get("hotkey"),
            "stats": c.history.stats(),
            "lastText": hist[0]["text"] if hist else "",
        }

    def get_modes(self) -> list:
        return [mode_ui_dict(m) for m in self.c.modes.list()]

    def get_history(self, query: str = "") -> list:
        return self.c.history.list(query=query or "")

    def get_settings(self) -> dict:
        return self.c.config.all(redact=True)

    # ---- writes ----
    def set_setting(self, key: str, value) -> bool:
        self.c.config.set(key, value)
        if key == "hotkey" and self.c.listener:
            self.c.listener.rebind(str(value))
        return True

    def set_active_mode(self, mode_id: str) -> bool:
        self.c._active_mode_id = mode_id
        self.c.config.set("activeMode", mode_id)
        return True

    def copy_text(self, text: str) -> bool:
        return paste.set_clipboard(text)

    def window_action(self, action: str) -> bool:
        win = self.c.main_window
        if not win:
            return False
        try:
            if action == "min":
                win.minimize()
            elif action == "close":
                win.hide()  # keep running in the background
        except Exception:
            return False
        return True
