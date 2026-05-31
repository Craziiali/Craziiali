#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CRAZIIALI — Laptop Alarm Agent (Windows 11)
===========================================
Listens to the Firebase Realtime Database "alarms" node. When you press the
"Add to Calendar" button in the planner, the website writes an alarm record
here. This agent rings a REAL, LOUD Windows alarm that LOOPS UNTIL DISMISSED,
both 1 HOUR BEFORE and AT THE EXACT shoot time — even if every browser is
closed. The only requirement is that this agent is running (it auto-starts
with Windows once you set that up; see README.txt).

No sound file needed — the agent generates its own siren WAV on first run.
No internet downloads per alarm — everything is instant over Firebase.
"""

import os
import sys
import json
import time
import math
import wave
import struct
import socket
import threading
from datetime import datetime, timedelta

# ── Third-party (installed by install.bat) ─────────────────────────────
try:
    import firebase_admin
    from firebase_admin import credentials, db
except ImportError:
    print("\n[!] firebase-admin is not installed.")
    print("    Double-click  install.bat  in this folder first, then run again.\n")
    input("Press Enter to close...")
    sys.exit(1)

# ── Windows-only sound ─────────────────────────────────────────────────
try:
    import winsound
except ImportError:
    print("\n[!] This agent only runs on Windows.\n")
    sys.exit(1)

import tkinter as tk

# ── Configuration ──────────────────────────────────────────────────────
HERE          = os.path.dirname(os.path.abspath(__file__))
KEY_PATH      = os.path.join(HERE, "serviceAccountKey.json")
WAV_PATH      = os.path.join(HERE, "alarm.wav")
STATE_PATH    = os.path.join(HERE, "fired.json")
DATABASE_URL  = "https://my-figma-a7909-default-rtdb.europe-west1.firebasedatabase.app"

CHECK_SECONDS   = 2          # how often we check the clock (local, free) -> alarm fires within ~2s
REFRESH_SECONDS = 20         # how often we re-download alarms from Firebase (network)
GRACE_MINUTES = 5            # only ring if we're within this many minutes AFTER the trigger
                             # (so booting up hours later doesn't ring for shoots already past)
SNOOZE_MINUTES = 5           # snooze button delay


# ── Generate a loud two-tone siren WAV on first run (no download needed) ─
def ensure_wav():
    if os.path.exists(WAV_PATH):
        return
    framerate = 44100
    amp = 0.75 * 32767          # loud
    seg = 0.28                  # seconds per tone
    tones = [880, 1175, 880, 1175]   # urgent back-and-forth
    frames = bytearray()
    for freq in tones:
        n = int(framerate * seg)
        for i in range(n):
            # slight attack/decay so it doesn't click harshly
            env = min(1.0, i / 400.0, (n - i) / 400.0)
            val = int(amp * env * math.sin(2 * math.pi * freq * (i / framerate)))
            frames += struct.pack("<h", val)
    with wave.open(WAV_PATH, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(framerate)
        w.writeframes(bytes(frames))


# ── Persisted "already fired" state ─────────────────────────────────────
def load_state():
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_state(state):
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception as e:
        print("[!] could not save state:", e)


# ── Parse the website's date ("YYYY.MM.DD") + time ("HH:MM") ────────────
def shoot_datetime(rec):
    date = str(rec.get("date", ""))
    tm   = str(rec.get("time", ""))
    parts = date.replace("-", ".").replace("/", ".").split(".")
    m = tm.split(":")
    if len(parts) != 3 or len(m) != 2:
        return None
    try:
        return datetime(int(parts[0]), int(parts[1]), int(parts[2]), int(m[0]), int(m[1]))
    except ValueError:
        return None

def fmt12(dt):
    h = dt.hour % 12 or 12
    ap = "AM" if dt.hour < 12 else "PM"
    return "%d:%02d %s" % (h, dt.minute, ap)


# ── THE ALARM: loud looping sound + fullscreen dismissable window ───────
_ringing = threading.Event()

def stop_sound():
    try:
        winsound.PlaySound(None, 0)
    except Exception:
        pass

def ring(title, when_label, shoot_dt, location, notes):
    """Shows a compact popup in the top-right corner that floats above other
    windows but does NOT take over the screen or steal keyboard focus — so it
    won't interrupt or crash whatever you're working in (Premiere, etc.).
    The siren loops until you click DISMISS or SNOOZE. Returns 'dismiss'/'snooze'."""
    _ringing.set()
    # Loop the siren in the background until we stop it.
    try:
        winsound.PlaySound(WAV_PATH, winsound.SND_FILENAME | winsound.SND_LOOP | winsound.SND_ASYNC)
    except Exception as e:
        print("[!] sound error:", e)

    result = {"action": "dismiss"}

    CARD_W, CARD_H = 400, 0  # height auto-grows to fit content
    root = tk.Tk()
    root.title("CRAZIIALI")
    root.configure(bg="#16161c")
    root.overrideredirect(True)         # borderless card (no title bar)
    root.attributes("-topmost", True)   # floats above other windows
    try: root.attributes("-alpha", 0.0)  # fade in
    except Exception: pass

    # Accent strip down the left edge
    accent = tk.Frame(root, bg="#7e8cf7", width=4)
    accent.pack(side="left", fill="y")

    pad = tk.Frame(root, bg="#16161c")
    pad.pack(side="left", fill="both", expand=True, padx=20, pady=18)

    tk.Label(pad, text=when_label, font=("Consolas", 12, "bold"),
             fg="#9aa6ff", bg="#16161c", anchor="w").pack(fill="x", pady=(0, 6))
    tk.Label(pad, text=title, font=("Georgia", 22, "bold italic"),
             fg="#f3f3ef", bg="#16161c", wraplength=CARD_W - 60, justify="left",
             anchor="w").pack(fill="x", pady=(0, 8))
    tk.Label(pad, text="Shoot at  " + fmt12(shoot_dt), font=("Consolas", 13),
             fg="#cdd1ff", bg="#16161c", anchor="w").pack(fill="x")
    if location:
        tk.Label(pad, text=location, font=("Consolas", 10),
                 fg="#8a90a0", bg="#16161c", wraplength=CARD_W - 60, justify="left",
                 anchor="w").pack(fill="x", pady=(4, 0))
    if notes:
        tk.Label(pad, text=notes, font=("Consolas", 10),
                 fg="#75798a", bg="#16161c", wraplength=CARD_W - 60, justify="left",
                 anchor="w").pack(fill="x", pady=(3, 0))

    btns = tk.Frame(pad, bg="#16161c")
    btns.pack(fill="x", pady=(16, 0))

    def do_dismiss():
        result["action"] = "dismiss"
        stop_sound(); _ringing.clear(); root.destroy()

    def do_snooze():
        result["action"] = "snooze"
        stop_sound(); _ringing.clear(); root.destroy()

    tk.Button(btns, text="DISMISS", font=("Consolas", 12, "bold"),
              fg="#0a0a0b", bg="#f3f3ef", activebackground="#ffffff",
              relief="flat", padx=22, pady=9, cursor="hand2", command=do_dismiss).pack(side="left", padx=(0, 8))
    tk.Button(btns, text="SNOOZE %dm" % SNOOZE_MINUTES, font=("Consolas", 12, "bold"),
              fg="#f3f3ef", bg="#2a2a36", activebackground="#363644",
              relief="flat", padx=18, pady=9, cursor="hand2", command=do_snooze).pack(side="left")

    # Position in the top-right corner, just under the screen edge.
    root.update_idletasks()
    w = root.winfo_width()
    h = root.winfo_height()
    sw = root.winfo_screenwidth()
    x = sw - w - 24
    y = 24
    root.geometry("+%d+%d" % (x, y))

    # Float on top WITHOUT stealing keyboard focus (so it can't interrupt typing
    # or playback in another app). We deliberately do NOT call focus_force().
    root.lift()
    root.after(120, lambda: root.attributes("-topmost", True))

    # Gentle fade-in
    def fade(a=0.0):
        a = min(1.0, a + 0.12)
        try: root.attributes("-alpha", a)
        except Exception: pass
        if a < 1.0:
            root.after(16, lambda: fade(a))
    root.after(10, fade)

    # Re-assert sound + topmost every 3s in case something interrupts it
    def keep_ringing():
        if _ringing.is_set():
            try:
                winsound.PlaySound(WAV_PATH, winsound.SND_FILENAME | winsound.SND_LOOP | winsound.SND_ASYNC)
                root.attributes("-topmost", True)
            except Exception:
                pass
            root.after(3000, keep_ringing)
    root.after(3000, keep_ringing)

    root.mainloop()
    stop_sound()
    return result["action"]


# ── Single-instance guard ───────────────────────────────────────────────
# Bind a fixed local port. If it's already taken, another copy of the agent
# is running, so this one exits — preventing the alarm from popping up twice
# (e.g. if autostart launches while a copy is already running).
_lock_sock = None
def already_running():
    global _lock_sock
    try:
        _lock_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _lock_sock.bind(("127.0.0.1", 50507))
        _lock_sock.listen(1)
        return False
    except OSError:
        return True


# ── Main loop ───────────────────────────────────────────────────────────
def main():
    print("=" * 56)
    print("  CRAZIIALI — Laptop Alarm Agent")
    print("=" * 56)

    if already_running():
        print("\n[i] Another copy of the alarm agent is already running. Exiting.\n")
        return

    if not os.path.exists(KEY_PATH):
        print("\n[!] Missing serviceAccountKey.json in this folder.")
        print("    See README.txt → Step 3 (download it from Firebase).\n")
        input("Press Enter to close...")
        sys.exit(1)

    ensure_wav()

    try:
        cred = credentials.Certificate(KEY_PATH)
        firebase_admin.initialize_app(cred, {"databaseURL": DATABASE_URL})
    except Exception as e:
        print("\n[!] Could not connect to Firebase:", e, "\n")
        input("Press Enter to close...")
        sys.exit(1)

    ref = db.reference("alarms")
    state = load_state()
    print("\n[ok] Connected. Watching for shoots... (leave this running)")
    print("     Rings 1 hour before each shoot. Loops until you dismiss.\n")

    # Snooze list: (fire_at_datetime, title, label, shoot_dt, location, notes)
    snoozes = []
    data = {}
    last_fetch = 0.0   # monotonic timestamp of the last Firebase fetch

    while True:
        now = datetime.now()

        # 1) Fire any due snoozes first
        still = []
        for s in snoozes:
            if now >= s[0]:
                act = ring(s[1], s[2], s[3], s[4], s[5])
                if act == "snooze":
                    still.append((now + timedelta(minutes=SNOOZE_MINUTES), s[1], s[2], s[3], s[4], s[5]))
            else:
                still.append(s)
        snoozes = still

        # 2) Re-download alarms from Firebase only every REFRESH_SECONDS (network is the
        #    slow part). The clock check below still runs every CHECK_SECONDS, so an alarm
        #    fires within ~2s of its time without hammering the database.
        if time.monotonic() - last_fetch >= REFRESH_SECONDS:
            try:
                data = ref.get() or {}
            except Exception as e:
                print("[!] read error:", e)
            last_fetch = time.monotonic()

        # 3) Check each alarm's two triggers
        for aid, rec in (data.items() if isinstance(data, dict) else []):
            if not isinstance(rec, dict):
                continue
            sdt = shoot_datetime(rec)
            if not sdt:
                continue
            title    = rec.get("title", "Shoot")
            location = rec.get("location", "")
            notes    = rec.get("notes", "")

            triggers = [
                ("before", sdt - timedelta(hours=1),     "SHOOT IN 1 HOUR"),
            ]
            for kind, trig, label in triggers:
                key = "%s|%s|%s" % (aid, kind, trig.isoformat())
                if state.get(key):
                    continue  # already handled
                # Only ring inside the grace window [trig, trig+grace]
                if trig <= now <= trig + timedelta(minutes=GRACE_MINUTES):
                    state[key] = True
                    save_state(state)
                    act = ring(title, label, sdt, location, notes)
                    if act == "snooze":
                        snoozes.append((datetime.now() + timedelta(minutes=SNOOZE_MINUTES),
                                        title, label, sdt, location, notes))
                # Mark long-past triggers as handled so they never ring on a late boot
                elif now > trig + timedelta(minutes=GRACE_MINUTES):
                    state[key] = True
                    save_state(state)

        # 4) Prune state entries for triggers far in the past (keep file small)
        cutoff = (now - timedelta(days=30))
        pruned = {}
        for k, v in state.items():
            try:
                iso = k.split("|")[-1]
                if datetime.fromisoformat(iso) >= cutoff:
                    pruned[k] = v
            except Exception:
                pruned[k] = v
        if len(pruned) != len(state):
            state = pruned
            save_state(state)

        time.sleep(CHECK_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        stop_sound()
        print("\nStopped.")
