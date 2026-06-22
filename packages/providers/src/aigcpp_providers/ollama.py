"""Ollama chat adapter."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from .base import ModelProvider, ProviderError


class OllamaProvider(ModelProvider):
    name = "ollama"

    def __init__(self, *, base_url: str, model: str) -> None:
        if not base_url.strip():
            raise ProviderError("base_url is required for Ollama provider")
        if not model.strip():
            raise ProviderError("model is required for Ollama provider")
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate_text(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: float = 120,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ProviderError(f"Ollama request failed: {exc}") from exc
        data = json.loads(raw)
        try:
            return str(data["message"]["content"])
        except (KeyError, TypeError) as exc:
            raise ProviderError("Ollama response did not include message content") from exc
