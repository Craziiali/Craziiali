/* ============================================================================
   Murmur — pill overlay controller
   Driven by the Python backend, which calls window.pill.* as state changes.
   Also self-animates a live waveform from amplitude updates.
   ============================================================================ */

"use strict";

const BARS = 9;
const waveEl = document.getElementById("wave");
const orbEl = document.getElementById("pillOrb");
const pillEl = document.getElementById("pill");
const stateText = document.getElementById("stateText");
const modeText = document.getElementById("modeText");
const timerEl = document.getElementById("timer");

// build bars
for (let i = 0; i < BARS; i++) {
  const b = document.createElement("div");
  b.className = "bar";
  waveEl.appendChild(b);
}
const bars = [...waveEl.children];

const STATE_LABELS = {
  idle: "Ready",
  listening: "Listening…",
  transcribing: "Transcribing…",
  polishing: "Polishing…",
  done: "Done ✓",
};

let timerStart = 0, timerRAF = 0;

const pill = {
  setState(state) {
    pillEl.dataset.state = state;
    stateText.textContent = STATE_LABELS[state] || state;
    if (state === "listening") this.startTimer();
    else this.stopTimer();
    if (state === "idle" || state === "done") this.setAmp(0);
  },

  setMode(name, hint) {
    modeText.textContent = hint ? `${name} · ${hint}` : name;
  },

  /* amplitude 0..1 — drives orb scale/glow and pushes a new bar height */
  setAmp(amp) {
    amp = Math.max(0, Math.min(1, amp));
    orbEl.style.setProperty("--amp", amp.toFixed(3));
    document.querySelector(".pill__orb-wrap").style.setProperty("--amp", amp.toFixed(3));
    if (pillEl.dataset.state === "listening") this.pushLevel(amp);
  },

  /* scrolling live levels while recording */
  pushLevel(amp) {
    for (let i = 0; i < bars.length - 1; i++) {
      bars[i].style.height = bars[i + 1].style.height || "18%";
    }
    const h = 18 + amp * 78 + Math.random() * 6;
    bars[bars.length - 1].style.height = `${Math.min(100, h)}%`;
  },

  startTimer() {
    timerStart = performance.now();
    const tick = () => {
      const s = (performance.now() - timerStart) / 1000;
      const m = Math.floor(s / 60);
      timerEl.textContent = `${m}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
      timerRAF = requestAnimationFrame(tick);
    };
    cancelAnimationFrame(timerRAF);
    tick();
  },
  stopTimer() { cancelAnimationFrame(timerRAF); },
};

window.pill = pill;

// Demo loop in a plain browser (no backend): cycle through states + fake levels.
if (!(window.pywebview && window.pywebview.api)) {
  let fakeAmp = 0;
  setInterval(() => {
    if (pillEl.dataset.state === "listening") {
      fakeAmp = Math.max(0, Math.min(1, fakeAmp + (Math.random() - 0.45) * 0.5));
      pill.setAmp(fakeAmp);
    }
  }, 90);
}
