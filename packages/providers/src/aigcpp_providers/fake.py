"""Deterministic provider for tests, demos, and offline smoke runs."""

from __future__ import annotations

import json

from .base import ModelProvider


class FakeProvider(ModelProvider):
    name = "fake"

    def __init__(self, *, model: str = "fake-model") -> None:
        self.model = model

    def generate_text(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: float = 120,
    ) -> str:
        prompt = "\n".join(message.get("content", "") for message in messages)
        if "JSON_OBJECT" in prompt:
            return json.dumps({"ok": True, "model": self.model}, ensure_ascii=False)
        if "COMPLETE_NOVEL" in prompt:
            return ""
        return "deterministic fake provider response"
