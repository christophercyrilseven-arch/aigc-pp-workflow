"""OpenAI-compatible chat completions adapter."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from .base import ModelProvider, ProviderError


class OpenAICompatibleProvider(ModelProvider):
    name = "openai-compatible"

    def __init__(self, *, base_url: str, model: str, api_key: str = "") -> None:
        if not base_url.strip():
            raise ProviderError("base_url is required for OpenAI-compatible provider")
        if not model.strip():
            raise ProviderError("model is required for OpenAI-compatible provider")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key

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
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ProviderError(f"OpenAI-compatible request failed: {exc}") from exc
        data = json.loads(raw)
        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("OpenAI-compatible response did not include message content") from exc
