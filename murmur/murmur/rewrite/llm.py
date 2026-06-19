"""The AI rewriting step that powers Modes.

Takes a mode + raw transcript + context, builds messages, and asks an LLM to
produce the finished text. Supports OpenAI and Anthropic. If the mode doesn't
rewrite (verbatim) or no key is set, it safely returns the transcript unchanged.
"""
from __future__ import annotations

from ..config import Config
from ..modes import Mode, build_rewrite_messages

# Sensible default models if a mode doesn't specify one.
DEFAULT_OPENAI = "gpt-4o-mini"
DEFAULT_ANTHROPIC = "claude-haiku-4-5"


class Rewriter:
    def __init__(self, config: Config):
        self.config = config

    def rewrite(self, mode: Mode, transcript: str, context: dict | None = None) -> str:
        if not mode.rewrites:
            return transcript

        messages = build_rewrite_messages(mode, transcript, context)
        if not messages:
            return transcript

        provider = mode.llm_provider
        try:
            if provider == "anthropic":
                return self._anthropic(mode, messages) or transcript
            if provider == "openai":
                return self._openai(mode, messages) or transcript
        except Exception:
            # Rewriting is a nicety — never lose the user's words if the LLM fails.
            return transcript
        return transcript

    # ------------------------------------------------------------------ #
    def _openai(self, mode: Mode, messages: list[dict]) -> str:
        key = self.config.get("openaiKey", "")
        if not key:
            return ""
        from openai import OpenAI
        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model=mode.llm_model or DEFAULT_OPENAI,
            messages=messages,
            temperature=0.3,
        )
        return (resp.choices[0].message.content or "").strip()

    def _anthropic(self, mode: Mode, messages: list[dict]) -> str:
        key = self.config.get("anthropicKey", "")
        if not key:
            return ""
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user = [m for m in messages if m["role"] != "system"]
        resp = client.messages.create(
            model=mode.llm_model or DEFAULT_ANTHROPIC,
            system=system,
            max_tokens=2000,
            temperature=0.3,
            messages=user,
        )
        parts = [blk.text for blk in resp.content if getattr(blk, "type", "") == "text"]
        return "".join(parts).strip()
