"""Shared provider contracts."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any


class ProviderError(RuntimeError):
    """Raised when a model provider cannot complete a request."""


class ModelProvider(ABC):
    """Minimal text and JSON generation contract used by the workflow."""

    name: str

    @abstractmethod
    def generate_text(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: float = 120,
    ) -> str:
        """Generate free-form text from chat messages."""

    def generate_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int = 2000,
        timeout: float = 120,
    ) -> dict[str, Any]:
        """Generate and parse a JSON object, with one lightweight extraction pass."""
        text = self.generate_text(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                raise ProviderError("model output did not contain a JSON object") from None
            parsed = json.loads(match.group(0))
        if not isinstance(parsed, dict):
            raise ProviderError("model JSON output must be an object")
        return parsed
