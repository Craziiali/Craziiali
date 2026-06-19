/* ============================================================================
   Murmur — main window controller
   Talks to the Python backend through `window.pywebview.api` when running
   inside the app. In a plain browser it falls back to local mock data so the
   whole UI is viewable and clickable for design + development.
   ============================================================================ */

"use strict";

/* ---------------------------- Bridge ----------------------------------- */
const hasNative = () => !!(window.pywebview && window.pywebview.api);

const Bridge = {
  async call(method, ...args) {
    if (hasNative() && typeof window.pywebview.api[method] === "function") {
      try { return await window.pywebview.api[method](...args); }
      catch (e) { console.error(`bridge ${method} failed`, e); return null; }
    }
    return Mock[method] ? Mock[method](...args) : null;
  },
};

/* ------------------------- Mock data (browser) ------------------------- */
const Mock = {
  get_state: () => ({
    engine: { mode: "local", model: "base", online: true },
    mic: { ready: true, name: "MacBook Pro Microphone" },
    activeMode: "voice",
    theme: "dark",
    stats: { words: 18420, sessions: 312, minutesSaved: 214 },
    hotkey: "Alt+Space",
    lastText:
      "Sure — let's move the launch review to Thursday at 2pm and loop in the design team so we can walk through the new onboarding flow together.",
  }),
  get_modes: () => DEFAULT_MODES,
  get_history: () => DEFAULT_HISTORY,
  get_settings: () => DEFAULT_SETTINGS,
  set_setting: () => true,
  set_active_mode: () => true,
  copy_text: () => true,
};

/* ------------------------- Built-in mode set --------------------------- */
const DEFAULT_MODES = [
  { id: "voice", name: "Voice", glyph: "✶", key: "Alt+Space",
    desc: "Clean, faithful transcription with punctuation. No rewriting — your words, tidied.",
    transModel: "Local · base", llm: "—", tags: ["Offline", "Verbatim"] },
  { id: "message", name: "Message", glyph: "💬", key: "Alt+1",
    desc: "Casual, concise chat tone. Trims filler, keeps it human for Slack and texts.",
    transModel: "Local · base", llm: "GPT", tags: ["Casual", "Auto: Slack"] },
  { id: "mail", name: "Mail", glyph: "✉️", key: "Alt+2",
    desc: "Formats into a polished email — greeting, body, sign-off — matching the thread's tone.",
    transModel: "Cloud · whisper", llm: "Claude", tags: ["Formal", "Auto: Gmail"] },
  { id: "note", name: "Note", glyph: "📝", key: "Alt+3",
    desc: "Turns rambling thoughts into clean bullet points and short paragraphs.",
    transModel: "Local · small", llm: "GPT", tags: ["Structured"] },
  { id: "meeting", name: "Meeting", glyph: "🎙️", key: "Alt+4",
    desc: "Long-form capture with speaker-friendly paragraphs and a summary at the end.",
    transModel: "Local · large-v3", llm: "Claude", tags: ["Long-form", "Summary"] },
  { id: "code", name: "Code", glyph: "⌘", key: "Alt+5",
    desc: "Dictate commands and prompts for Cursor, Claude Code & terminals. Keeps symbols literal.",
    transModel: "Local · base", llm: "—", tags: ["Verbatim", "Dev"] },
];

/* ------------------------------ History -------------------------------- */
const DEFAULT_HISTORY = [
  { glyph: "✉️", mode: "Mail", ago: "2 min ago", dur: "0:24", words: 64,
    text: "Hi Sarah, thanks for the quick turnaround on the mockups. I've left a few comments in Figma — mostly around spacing on the pricing cards. Could we sync tomorrow morning to finalize before the review?" },
  { glyph: "💬", mode: "Message", ago: "18 min ago", dur: "0:06", words: 14,
    text: "On my way, grabbing coffee first — want anything?" },
  { glyph: "📝", mode: "Note", ago: "1 hr ago", dur: "0:41", words: 88,
    text: "Ideas for the onboarding redesign: 1) Move the model download into the background. 2) Add a 10-second voice test so people hear it work. 3) Default to the Voice mode and reveal advanced modes later." },
  { glyph: "✶", mode: "Voice", ago: "3 hrs ago", dur: "0:12", words: 31,
    text: "The quarterly numbers look strong, especially retention in the second cohort which is up about nine percent." },
  { glyph: "🎙️", mode: "Meeting", ago: "Yesterday", dur: "12:38", words: 1840,
    text: "Standup — backend is unblocked on the transcription queue, design is reviewing the orb animation, and we agreed to ship the Windows beta on Friday…" },
];

/* ------------------------------ Settings ------------------------------- */
const DEFAULT_SETTINGS = {
  theme: "dark",
  engine: "auto",
  localModel: "base",
  language: "auto",
  hotkey: "Alt+Space",
  launchAtLogin: true,
  playSounds: true,
  autoPaste: true,
  trimFillers: true,
  openaiKey: "",
  anthropicKey: "",
  microphone: "default",
};

/* ============================= Rendering =============================== */
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const esc = (s) => String(s).replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

let STATE = null;
let MODES = DEFAULT_MODES;
let HISTORY = DEFAULT_HISTORY;
let SETTINGS = DEFAULT_SETTINGS;

async function boot() {
  STATE = await Bridge.call("get_state");
  MODES = (await Bridge.call("get_modes")) || DEFAULT_MODES;
  HISTORY = (await Bridge.call("get_history")) || DEFAULT_HISTORY;
  SETTINGS = (await Bridge.call("get_settings")) || DEFAULT_SETTINGS;
  applyTheme(STATE.theme);
  renderDictate();
  renderModes();
  renderHistory();
  renderSettings();
  wireNav();
  wireMisc();
}

function applyTheme(theme) {
  const t = theme === "auto"
    ? (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark")
    : theme;
  document.documentElement.dataset.theme = t;
}

/* ---- Dictate ---- */
function renderDictate() {
  $("#lastText").textContent = STATE.lastText;
  const chip = $("#activeModeChip");
  const m = MODES.find((x) => x.id === STATE.activeMode) || MODES[0];
  chip.querySelector(".modechip__icon").textContent = m.glyph;
  chip.querySelector(".modechip__name").textContent = m.name;

  $("#engineStat .statline__text").textContent =
    STATE.engine.mode === "local" ? `Local · ${STATE.engine.model}` : "Cloud · whisper";
  $("#micStat .statline__text").textContent =
    STATE.mic.ready ? "Microphone ready" : "No microphone";

  const s = STATE.stats;
  $("#statRow").innerHTML = `
    ${stat(s.words.toLocaleString(), "words", "dictated")}
    ${stat(s.minutesSaved, "min", "time saved")}
    ${stat(s.sessions, "", "sessions")}`;
}
const stat = (num, unit, label) => `
  <div class="stat">
    <div class="stat__num">${esc(num)}${unit ? `<small>${esc(unit)}</small>` : ""}</div>
    <div class="stat__label">${esc(label)}</div>
  </div>`;

/* ---- Modes ---- */
function renderModes() {
  $("#modeGrid").innerHTML = MODES.map((m) => `
    <div class="modecard" data-mode="${esc(m.id)}">
      <div class="modecard__top">
        <div class="modecard__glyph">${m.glyph}</div>
        <div class="modecard__name">${esc(m.name)}</div>
        <div class="modecard__key">${esc(m.key)}</div>
      </div>
      <p class="modecard__desc">${esc(m.desc)}</p>
      <div class="modecard__tags">
        <span class="tag tag--accent">${esc(m.transModel)}</span>
        ${m.llm !== "—" ? `<span class="tag">AI · ${esc(m.llm)}</span>` : ""}
        ${m.tags.map((t) => `<span class="tag">${esc(t)}</span>`).join("")}
      </div>
    </div>`).join("");
}

/* ---- History ---- */
function renderHistory(filter = "") {
  const f = filter.trim().toLowerCase();
  const rows = HISTORY.filter((h) =>
    !f || h.text.toLowerCase().includes(f) || h.mode.toLowerCase().includes(f));
  $("#historyList").innerHTML = rows.length ? rows.map((h) => `
    <div class="histrow">
      <div class="histrow__glyph">${h.glyph}</div>
      <div class="histrow__body">
        <div class="histrow__text">${esc(h.text)}</div>
        <div class="histrow__meta">
          <span>${esc(h.mode)}</span><span class="sep">·</span>
          <span>${esc(h.ago)}</span><span class="sep">·</span>
          <span>${esc(h.dur)}</span><span class="sep">·</span>
          <span>${h.words} words</span>
        </div>
      </div>
      <button class="histrow__copy" title="Copy" data-copy="${esc(h.text)}">
        <svg viewBox="0 0 24 24" class="ic"><rect x="9" y="9" width="11" height="11" rx="2.5" class="stroke"/><path class="stroke" d="M5 15V5.5A1.5 1.5 0 0 1 6.5 4H15"/></svg>
      </button>
    </div>`).join("") : `<div class="livecard"><p class="livecard__text">No dictations match “${esc(filter)}”.</p></div>`;
}

/* ---- Settings ---- */
function renderSettings() {
  const s = SETTINGS;
  $("#settingsBody").innerHTML = `
    <div class="sgroup">
      <div class="sgroup__title">Appearance</div>
      <div class="scard">
        ${rowSegment("Theme", "Match the system, or pick a side.", "theme",
          [["auto","Auto"],["light","Light"],["dark","Dark"]], s.theme)}
      </div>
    </div>

    <div class="sgroup">
      <div class="sgroup__title">Transcription Engine</div>
      <div class="scard">
        ${rowSegment("Engine", "Auto uses local Whisper offline and the cloud when you're connected.",
          "engine", [["auto","Auto"],["local","Local"],["cloud","Cloud"]], s.engine)}
        ${rowSelect("Local model", "Bigger is more accurate but slower. base is a great default.",
          "localModel", [["tiny","tiny · fastest"],["base","base · balanced"],
          ["small","small"],["medium","medium"],["large-v3","large-v3 · best"]], s.localModel)}
        ${rowSelect("Language", "Force a language, or let Murmur detect it.",
          "language", [["auto","Detect"],["en","English"],["es","Spanish"],["fr","French"],
          ["de","German"],["ar","Arabic"],["zh","Chinese"]], s.language)}
      </div>
    </div>

    <div class="sgroup">
      <div class="sgroup__title">Dictation</div>
      <div class="scard">
        ${rowKbd("Hotkey", "Hold to record, release to paste.", s.hotkey)}
        ${rowToggle("Paste automatically", "Drop text at your cursor when you release.", "autoPaste", s.autoPaste)}
        ${rowToggle("Trim filler words", "Remove “um”, “uh”, and false starts.", "trimFillers", s.trimFillers)}
        ${rowToggle("Sound feedback", "A soft cue on start, stop, and paste.", "playSounds", s.playSounds)}
      </div>
    </div>

    <div class="sgroup">
      <div class="sgroup__title">AI Keys <span style="text-transform:none;letter-spacing:0;color:var(--text-quaternary)">· stored locally, only used for cloud modes</span></div>
      <div class="scard">
        ${rowKey("OpenAI", "For cloud transcription and GPT rewriting.", "openaiKey", s.openaiKey)}
        ${rowKey("Anthropic", "For Claude-powered rewriting.", "anthropicKey", s.anthropicKey)}
      </div>
    </div>

    <div class="sgroup">
      <div class="sgroup__title">System</div>
      <div class="scard">
        ${rowToggle("Launch at login", "Murmur waits quietly in the background.", "launchAtLogin", s.launchAtLogin)}
      </div>
    </div>`;
}

const rowShell = (label, hint, control) => `
  <div class="srow">
    <div class="srow__main"><div class="srow__label">${esc(label)}</div>
    ${hint ? `<div class="srow__hint">${hint}</div>` : ""}</div>
    <div class="srow__control">${control}</div>
  </div>`;
const rowSegment = (l, h, key, opts, val) => rowShell(l, h,
  `<div class="segment" data-setting="${key}">${opts.map(([v, t]) =>
    `<button data-val="${v}" class="${v === val ? "is-active" : ""}">${t}</button>`).join("")}</div>`);
const rowSelect = (l, h, key, opts, val) => rowShell(l, h,
  `<select class="field field--select" data-setting="${key}">${opts.map(([v, t]) =>
    `<option value="${v}" ${v === val ? "selected" : ""}>${t}</option>`).join("")}</select>`);
const rowToggle = (l, h, key, on) => rowShell(l, h,
  `<div class="toggle ${on ? "is-on" : ""}" data-setting="${key}" role="switch" aria-checked="${on}"></div>`);
const rowKbd = (l, h, val) => rowShell(l, h,
  `<div class="kbdcapture">${val.split("+").map((k) => `<kbd>${esc(k)}</kbd>`).join("")}</div>`);
const rowKey = (l, h, key, val) => {
  const isSet = val === true || (typeof val === "string" && val.length > 0);
  return rowShell(l, h,
    `<input class="field field--key" type="password" autocomplete="off" spellcheck="false"
      placeholder="${isSet ? "•••••••••• saved" : "sk-…"}" data-setting="${key}" value="" />`);
};

/* ============================== Wiring ================================ */
function wireNav() {
  $$(".nav__item").forEach((btn) => btn.addEventListener("click", () => {
    const view = btn.dataset.view;
    $$(".nav__item").forEach((b) => b.classList.toggle("is-active", b === btn));
    $$(".view").forEach((v) => v.classList.toggle("is-active", v.dataset.view === view));
  }));
}

function wireMisc() {
  // copy buttons (history + last)
  document.addEventListener("click", (e) => {
    const copyBtn = e.target.closest("[data-copy]");
    if (copyBtn) { doCopy(copyBtn.dataset.copy); }
    const card = e.target.closest(".modecard");
    if (card) {
      const id = card.dataset.mode;
      Bridge.call("set_active_mode", id);
      STATE.activeMode = id;
      renderDictate();
      toast(`“${card.querySelector(".modecard__name").textContent}” is now active`);
    }
    const win = e.target.closest("[data-win]");
    if (win) { Bridge.call("window_action", win.dataset.win); }
  });
  $("#copyLast").addEventListener("click", () => doCopy(STATE.lastText));
  $("#historySearch").addEventListener("input", (e) => renderHistory(e.target.value));
  $("#newMode").addEventListener("click", () => toast("New mode — coming together ✨"));
  $("#activeModeChip").addEventListener("click", () => {
    $$(".nav__item").forEach((b) => b.classList.toggle("is-active", b.dataset.view === "modes"));
    $$(".view").forEach((v) => v.classList.toggle("is-active", v.dataset.view === "modes"));
  });

  // settings interactions
  document.addEventListener("click", (e) => {
    const seg = e.target.closest(".segment button");
    if (seg) {
      const wrap = seg.closest(".segment");
      $$("button", wrap).forEach((b) => b.classList.toggle("is-active", b === seg));
      const key = wrap.dataset.setting, val = seg.dataset.val;
      Bridge.call("set_setting", key, val);
      if (key === "theme") applyTheme(val);
    }
    const tog = e.target.closest(".toggle");
    if (tog) {
      const on = tog.classList.toggle("is-on");
      tog.setAttribute("aria-checked", on);
      Bridge.call("set_setting", tog.dataset.setting, on);
    }
  });
  document.addEventListener("change", (e) => {
    const sel = e.target.closest("select[data-setting], input[data-setting]");
    if (sel) Bridge.call("set_setting", sel.dataset.setting, sel.value);
  });
}

async function doCopy(text) {
  await Bridge.call("copy_text", text);
  try { await navigator.clipboard.writeText(text); } catch (_) {}
  toast("Copied to clipboard");
}

let toastTimer;
function toast(msg) {
  const el = $("#toast");
  el.textContent = msg;
  el.classList.add("is-show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("is-show"), 1900);
}

/* Python can push live updates into the UI via these globals */
window.murmur = {
  setState: (s) => { STATE = { ...STATE, ...s }; renderDictate(); },
  setLastText: (t) => { STATE.lastText = t; $("#lastText").textContent = t; },
  refreshHistory: async () => {
    HISTORY = (await Bridge.call("get_history")) || HISTORY;
    renderHistory($("#historySearch") ? $("#historySearch").value : "");
  },
  toast: (msg) => toast(msg),
};

window.addEventListener("pywebviewready", boot);
document.addEventListener("DOMContentLoaded", () => { if (!hasNative()) boot(); });
