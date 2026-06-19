"""Offline transcription via faster-whisper.

Lazily imported so the rest of the app runs (and tests pass) even when the
heavy dependency / model isn't installed yet. Models are cached under
paths.models_dir() so they download once.
"""
from __future__ import annotations

import functools

from .base import TranscriptResult, TranscriptionError
from .. import paths


@functools.lru_cache(maxsize=1)
def available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except Exception:
        return False


@functools.lru_cache(maxsize=4)
def _load(model_name: str):
    from faster_whisper import WhisperModel
    # int8 keeps it fast and light on CPU; CUDA users get a speed boost for free.
    return WhisperModel(
        model_name,
        device="auto",
        compute_type="int8",
        download_root=str(paths.models_dir()),
    )


def transcribe(audio_path: str, *, model: str = "base", language: str = "auto") -> TranscriptResult:
    if not available():
        raise TranscriptionError("faster-whisper is not installed.")
    whisper = _load(model)
    segments, info = whisper.transcribe(
        audio_path,
        language=None if language in ("", "auto") else language,
        vad_filter=True,                      # skip silence -> faster, cleaner
        beam_size=5,
    )
    text = "".join(seg.text for seg in segments).strip()
    return TranscriptResult(
        text=text,
        language=getattr(info, "language", "") or "",
        duration=getattr(info, "duration", 0.0) or 0.0,
        engine="local",
        model=model,
    )
