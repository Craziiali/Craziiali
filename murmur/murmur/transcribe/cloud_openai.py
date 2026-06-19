"""Online transcription via OpenAI's audio API.

Uses the official `openai` SDK when present; otherwise falls back to a small
multipart upload over urllib so cloud mode works with zero extra packages.
"""
from __future__ import annotations

import json
import uuid
import urllib.request

from .base import TranscriptResult, TranscriptionError

API_URL = "https://api.openai.com/v1/audio/transcriptions"
DEFAULT_MODEL = "whisper-1"


def available(api_key: str) -> bool:
    return bool(api_key)


def transcribe(audio_path: str, *, api_key: str, model: str = DEFAULT_MODEL,
               language: str = "auto") -> TranscriptResult:
    if not api_key:
        raise TranscriptionError("No OpenAI API key configured.")

    lang = None if language in ("", "auto") else language

    # Prefer the official SDK if installed.
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        with open(audio_path, "rb") as fh:
            kwargs = {"model": model, "file": fh}
            if lang:
                kwargs["language"] = lang
            resp = client.audio.transcriptions.create(**kwargs)
        text = (getattr(resp, "text", "") or "").strip()
        return TranscriptResult(text=text, language=lang or "", engine="cloud", model=model)
    except ImportError:
        pass  # fall through to urllib

    text = _multipart_transcribe(audio_path, api_key=api_key, model=model, language=lang)
    return TranscriptResult(text=text.strip(), language=lang or "", engine="cloud", model=model)


def _multipart_transcribe(audio_path, *, api_key, model, language) -> str:
    boundary = f"----murmur{uuid.uuid4().hex}"
    with open(audio_path, "rb") as fh:
        audio = fh.read()

    def field(name, value):
        return (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n").encode()

    body = bytearray()
    body += field("model", model)
    if language:
        body += field("language", language)
    body += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
             f'filename="audio.wav"\r\nContent-Type: audio/wav\r\n\r\n').encode()
    body += audio + b"\r\n"
    body += f"--{boundary}--\r\n".encode()

    req = urllib.request.Request(API_URL, data=bytes(body), method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode()).get("text", "")
    except Exception as e:  # noqa: BLE001
        raise TranscriptionError(f"Cloud transcription failed: {e}") from e
