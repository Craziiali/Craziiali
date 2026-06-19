"""High-level transcription facade.

Given a mode + the user's config, it picks an engine (honouring offline/online
state), runs it, and transparently falls back if the first choice fails.
"""
from __future__ import annotations

from . import local_whisper, cloud_openai
from .base import Capabilities, TranscriptResult, TranscriptionError, is_online, resolve_engine
from ..config import Config
from ..modes import Mode


class Transcriber:
    def __init__(self, config: Config):
        self.config = config

    def capabilities(self, *, check_online: bool = True) -> Capabilities:
        return Capabilities(
            local_available=local_whisper.available(),
            cloud_available=bool(self.config.get("openaiKey")),
            online=is_online() if check_online else True,
        )

    def transcribe(self, audio_path: str, mode: Mode) -> TranscriptResult:
        # The mode's engine wins; "auto" defers to the global setting.
        requested = mode.engine if mode.engine != "auto" else self.config.get("engine", "auto")
        caps = self.capabilities()
        chosen = resolve_engine(requested, caps)

        language = mode.language if mode.language != "auto" else self.config.get("language", "auto")
        local_model = mode.trans_model or self.config.get("localModel", "base")

        try:
            return self._run(chosen, audio_path, local_model, language)
        except TranscriptionError:
            fallback = "cloud" if chosen == "local" else "local"
            if self._usable(fallback, caps):
                return self._run(fallback, audio_path, local_model, language)
            raise

    # ------------------------------------------------------------------ #
    def _usable(self, engine: str, caps: Capabilities) -> bool:
        if engine == "local":
            return caps.local_available
        return caps.cloud_available and caps.online

    def _run(self, engine: str, audio_path: str, model: str, language: str) -> TranscriptResult:
        if engine == "local":
            return local_whisper.transcribe(audio_path, model=model, language=language)
        return cloud_openai.transcribe(
            audio_path, api_key=self.config.get("openaiKey", ""), language=language
        )
