"""Microphone capture.

Records 16 kHz mono audio (what Whisper wants) to a temporary WAV file, and
streams a live amplitude level (0..1) so the orb can react to your voice.

Depends on `sounddevice` + `numpy`, both imported lazily.
"""
from __future__ import annotations

import os
import wave
import tempfile
import threading
from typing import Callable, Optional

SAMPLE_RATE = 16_000
CHANNELS = 1


def available() -> bool:
    try:
        import sounddevice  # noqa: F401
        import numpy        # noqa: F401
        return True
    except Exception:
        return False


def list_microphones() -> list[dict]:
    if not available():
        return []
    import sounddevice as sd
    devices = []
    for i, d in enumerate(sd.query_devices()):
        if d.get("max_input_channels", 0) > 0:
            devices.append({"index": i, "name": d["name"]})
    return devices


class Recorder:
    """Start/stop microphone recording with live level metering."""

    def __init__(self, on_level: Optional[Callable[[float], None]] = None,
                 device: Optional[int | str] = None):
        self.on_level = on_level
        self.device = device
        self._stream = None
        self._frames: list = []
        self._lock = threading.Lock()
        self._recording = False

    @property
    def recording(self) -> bool:
        return self._recording

    def start(self) -> None:
        if self._recording or not available():
            return
        import numpy as np
        import sounddevice as sd

        self._frames = []
        self._recording = True

        def callback(indata, frames, time_info, status):  # noqa: ANN001
            with self._lock:
                self._frames.append(indata.copy())
            if self.on_level is not None:
                rms = float(np.sqrt(np.mean(np.square(indata, dtype=np.float64)) + 1e-12))
                # map RMS (~0..0.3 for speech) to a lively 0..1 curve
                level = min(1.0, (rms ** 0.5) * 3.2)
                try:
                    self.on_level(level)
                except Exception:
                    pass

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32",
            device=self.device if self.device not in (None, "default") else None,
            callback=callback, blocksize=1024,
        )
        self._stream.start()

    def stop(self) -> Optional[str]:
        """Stop and return the path to a WAV file (or None if nothing captured)."""
        if not self._recording:
            return None
        self._recording = False
        try:
            self._stream.stop()
            self._stream.close()
        finally:
            self._stream = None

        import numpy as np
        with self._lock:
            frames = list(self._frames)
            self._frames = []
        if not frames:
            return None

        audio = np.concatenate(frames, axis=0)
        pcm16 = np.clip(audio, -1.0, 1.0)
        pcm16 = (pcm16 * 32767).astype("<i2")

        fd, path = tempfile.mkstemp(suffix=".wav", prefix="murmur_")
        os.close(fd)
        with wave.open(path, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(pcm16.tobytes())
        return path

    def duration(self) -> float:
        with self._lock:
            total = sum(len(f) for f in self._frames)
        return total / SAMPLE_RATE
