"""Shared types and engine-selection logic for transcription.

`resolve_engine` is pure (no I/O) so it can be unit-tested exhaustively.
"""
from __future__ import annotations

import socket
from dataclasses import dataclass


@dataclass
class TranscriptResult:
    text: str
    language: str = ""
    duration: float = 0.0
    engine: str = ""        # "local" | "cloud"
    model: str = ""


@dataclass
class Capabilities:
    local_available: bool      # faster-whisper importable
    cloud_available: bool      # an API key is configured
    online: bool               # network reachable


class TranscriptionError(RuntimeError):
    pass


def is_online(timeout: float = 1.5) -> bool:
    """Best-effort connectivity check (no DNS dependence)."""
    for host in ("1.1.1.1", "8.8.8.8"):
        try:
            with socket.create_connection((host, 443), timeout=timeout):
                return True
        except OSError:
            continue
    return False


def resolve_engine(requested: str, caps: Capabilities) -> str:
    """Decide which engine to actually use.

    requested: "auto" | "local" | "cloud"
      * auto  — prefer local (private, offline-capable); fall back to cloud.
      * local — local if available; otherwise cloud as a fallback.
      * cloud — cloud if usable (online + key); otherwise local as a fallback.

    Raises TranscriptionError if nothing is usable.
    """
    cloud_usable = caps.cloud_available and caps.online

    if requested == "local":
        if caps.local_available:
            return "local"
        if cloud_usable:
            return "cloud"
        raise TranscriptionError(
            "Local transcription isn't installed and no cloud fallback is available."
        )

    if requested == "cloud":
        if cloud_usable:
            return "cloud"
        if caps.local_available:
            return "local"
        if caps.cloud_available and not caps.online:
            raise TranscriptionError("You're offline and local transcription isn't installed.")
        raise TranscriptionError("Add an API key to use cloud transcription.")

    # auto
    if caps.local_available:
        return "local"
    if cloud_usable:
        return "cloud"
    raise TranscriptionError(
        "No transcription engine ready. Install the local model or add an API key."
    )
