"""Dictation history — a tiny SQLite store, private to this device.

Records the raw transcript and the polished result for every dictation, with
the mode, duration and word count. Powers the History view and the stats.
"""
from __future__ import annotations

import time
import sqlite3
import threading
from typing import Any

from . import paths


def _fmt_ago(ts: float, now: float | None = None) -> str:
    now = now if now is not None else time.time()
    d = max(0, int(now - ts))
    if d < 60:
        return "just now"
    if d < 3600:
        m = d // 60
        return f"{m} min ago"
    if d < 86400:
        h = d // 3600
        return f"{h} hr{'s' if h != 1 else ''} ago"
    days = d // 86400
    return "Yesterday" if days == 1 else f"{days} days ago"


def _fmt_dur(seconds: float) -> str:
    s = int(round(seconds))
    return f"{s // 60}:{s % 60:02d}"


class History:
    def __init__(self, path=None):
        self._path = str(path or paths.history_db())
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        with self._lock:
            self._conn.execute(
                """CREATE TABLE IF NOT EXISTS dictations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    mode_id TEXT, mode_name TEXT, glyph TEXT,
                    raw TEXT, text TEXT,
                    duration REAL DEFAULT 0,
                    words INTEGER DEFAULT 0
                )"""
            )
            self._conn.commit()

    def add(self, *, mode_id: str, mode_name: str, glyph: str,
            raw: str, text: str, duration: float) -> int:
        words = len((text or "").split())
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO dictations (ts, mode_id, mode_name, glyph, raw, text, duration, words)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (time.time(), mode_id, mode_name, glyph, raw, text, duration, words),
            )
            self._conn.commit()
            return cur.lastrowid

    def list(self, *, query: str = "", limit: int = 200) -> list[dict[str, Any]]:
        with self._lock:
            if query:
                rows = self._conn.execute(
                    "SELECT * FROM dictations WHERE text LIKE ? OR mode_name LIKE ?"
                    " ORDER BY ts DESC LIMIT ?",
                    (f"%{query}%", f"%{query}%", limit),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM dictations ORDER BY ts DESC LIMIT ?", (limit,)
                ).fetchall()
        now = time.time()
        return [self._present(r, now) for r in rows]

    def delete(self, dictation_id: int) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM dictations WHERE id=?", (dictation_id,))
            self._conn.commit()

    def stats(self) -> dict[str, int]:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) n, COALESCE(SUM(words),0) w, COALESCE(SUM(duration),0) d FROM dictations"
            ).fetchone()
        words = int(row["w"])
        # ~40 wpm typing vs speaking: rough "time saved" estimate in minutes
        spoken_min = row["d"] / 60.0
        typed_min = words / 40.0
        saved = max(0, int(round(typed_min - spoken_min)))
        return {"sessions": int(row["n"]), "words": words, "minutesSaved": saved}

    @staticmethod
    def _present(r: sqlite3.Row, now: float) -> dict[str, Any]:
        return {
            "id": r["id"],
            "mode": r["mode_name"],
            "glyph": r["glyph"] or "✶",
            "text": r["text"] or "",
            "raw": r["raw"] or "",
            "ago": _fmt_ago(r["ts"], now),
            "dur": _fmt_dur(r["duration"] or 0),
            "words": r["words"] or 0,
        }
