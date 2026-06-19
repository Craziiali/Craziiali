"""Modes — the recipes that turn speech into the right kind of text.

A mode bundles:
  * a transcription choice (engine + model + language)
  * an optional LLM rewriting step (provider + model + a natural-language prompt)
  * context toggles (may the LLM see the active app / selection / clipboard?)
  * auto-activation rules (switch to this mode in certain apps or sites)

`build_rewrite_messages` turns a mode + raw transcript + live context into the
chat messages we send to the LLM. Pure and unit-tested.
"""
from __future__ import annotations

import json
import dataclasses
from dataclasses import dataclass, field, asdict
from typing import Any

from . import paths


@dataclass
class Mode:
    id: str
    name: str
    glyph: str = "✶"
    hotkey: str = ""
    desc: str = ""

    # transcription
    engine: str = "auto"          # auto | local | cloud
    trans_model: str = "base"     # whisper model for local; ignored for cloud auto
    language: str = "auto"

    # rewriting (the "AI" step). provider "none" => verbatim transcript.
    llm_provider: str = "none"    # none | openai | anthropic
    llm_model: str = ""           # e.g. gpt-4o-mini, claude-haiku-4-5
    prompt: str = ""              # plain-language instruction
    tone: str = ""               # optional: Formal | Casual | Legal | Chat

    # context the rewriter is allowed to read
    use_active_app: bool = False
    use_selection: bool = False
    use_clipboard: bool = False

    # auto-activation: substrings matched against active app / window title / url
    auto_apps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Mode":
        fields = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in fields})

    @property
    def rewrites(self) -> bool:
        return self.llm_provider not in ("", "none") and bool(self.prompt or self.tone)


# Built-in modes (mirrors the UI defaults). Users may edit or add more.
def default_modes() -> list[Mode]:
    return [
        Mode(id="voice", name="Voice", glyph="✶", hotkey="alt+space",
             desc="Clean, faithful transcription with punctuation.",
             engine="auto", trans_model="base", llm_provider="none"),
        Mode(id="message", name="Message", glyph="💬", hotkey="alt+1",
             desc="Casual, concise chat tone for Slack and texts.",
             engine="auto", trans_model="base",
             llm_provider="openai", llm_model="gpt-4o-mini", tone="Casual",
             prompt="Rewrite this as a casual, friendly chat message. Keep it short and natural. "
                    "Remove filler and false starts. Do not add anything I didn't say.",
             use_active_app=True, auto_apps=["slack", "discord", "messages", "whatsapp"]),
        Mode(id="mail", name="Mail", glyph="✉️", hotkey="alt+2",
             desc="Polished email with greeting, body and sign-off.",
             engine="cloud", trans_model="base",
             llm_provider="anthropic", llm_model="claude-haiku-4-5", tone="Formal",
             prompt="Turn this into a well-structured, professional email. Add an appropriate greeting "
                    "and sign-off. Match the tone of any quoted thread. Keep my meaning exact.",
             use_active_app=True, use_selection=True, auto_apps=["gmail", "outlook", "mail"]),
        Mode(id="note", name="Note", glyph="📝", hotkey="alt+3",
             desc="Clean bullet points from rambling thoughts.",
             engine="auto", trans_model="small",
             llm_provider="openai", llm_model="gpt-4o-mini",
             prompt="Organize this into clear notes: short paragraphs and bullet points where helpful. "
                    "Keep all the information; just make it readable."),
        Mode(id="meeting", name="Meeting", glyph="🎙️", hotkey="alt+4",
             desc="Long-form capture with a summary at the end.",
             engine="local", trans_model="large-v3",
             llm_provider="anthropic", llm_model="claude-haiku-4-5",
             prompt="Format this meeting transcript into readable paragraphs, then add a short "
                    "'Summary' and 'Action items' section at the end."),
        Mode(id="code", name="Code", glyph="⌘", hotkey="alt+5",
             desc="Dictate commands/prompts for dev tools; symbols stay literal.",
             engine="auto", trans_model="base", llm_provider="none",
             use_active_app=True, auto_apps=["cursor", "code", "terminal", "iterm", "claude"]),
    ]


class ModeStore:
    """Loads/saves the user's modes, seeding with defaults on first run."""

    def __init__(self, path=None):
        self._path = path or paths.modes_file()
        self._modes: list[Mode] = []
        self.load()

    def load(self) -> None:
        try:
            raw = json.loads(self._path.read_text("utf-8"))
            self._modes = [Mode.from_dict(d) for d in raw]
            if not self._modes:
                raise ValueError
        except (FileNotFoundError, json.JSONDecodeError, ValueError, OSError, TypeError):
            self._modes = default_modes()
            self.save()

    def save(self) -> None:
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps([m.to_dict() for m in self._modes], indent=2), "utf-8")
        tmp.replace(self._path)

    def list(self) -> list[Mode]:
        return list(self._modes)

    def get(self, mode_id: str) -> Mode | None:
        return next((m for m in self._modes if m.id == mode_id), None)

    def upsert(self, mode: Mode) -> None:
        for i, m in enumerate(self._modes):
            if m.id == mode.id:
                self._modes[i] = mode
                break
        else:
            self._modes.append(mode)
        self.save()

    def delete(self, mode_id: str) -> None:
        self._modes = [m for m in self._modes if m.id != mode_id]
        self.save()

    def match_auto(self, context: dict[str, str]) -> Mode | None:
        """Return the first mode whose auto_apps match the given context, if any."""
        hay = " ".join(str(context.get(k, "")) for k in ("app", "title", "url")).lower()
        if not hay.strip():
            return None
        for m in self._modes:
            if any(token.lower() in hay for token in m.auto_apps):
                return m
        return None


# --------------------------------------------------------------------------- #
# Prompt construction (pure)
# --------------------------------------------------------------------------- #
def build_rewrite_messages(mode: Mode, transcript: str, context: dict | None = None) -> list[dict]:
    """Build chat messages [{role, content}, ...] for the rewriting step.

    Returns an empty list when the mode does not rewrite (verbatim).
    """
    if not mode.rewrites:
        return []

    context = context or {}
    sys_lines = [
        "You are Murmur, a dictation assistant. You receive a raw speech-to-text",
        "transcript and rewrite it according to the instruction below.",
        "Output ONLY the finished text — no preamble, no quotes, no explanations.",
        "Never invent facts or add content the speaker did not say.",
    ]
    if mode.tone:
        sys_lines.append(f"Target tone: {mode.tone}.")

    system = "\n".join(sys_lines)

    parts = [f"Instruction: {mode.prompt.strip() or 'Clean up the transcript.'}"]

    if mode.use_active_app and context.get("app"):
        parts.append(f"\nActive app: {context['app']}")
    if mode.use_selection and context.get("selection"):
        parts.append(f"\nSelected text the user is replying to:\n\"\"\"\n{context['selection']}\n\"\"\"")
    if mode.use_clipboard and context.get("clipboard"):
        parts.append(f"\nClipboard contents:\n\"\"\"\n{context['clipboard']}\n\"\"\"")

    parts.append(f"\nTranscript to rewrite:\n\"\"\"\n{transcript.strip()}\n\"\"\"")

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n".join(parts)},
    ]
