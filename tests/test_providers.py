from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from aigcpp_providers.base import ModelProvider
from aigcpp_providers.ollama import OllamaProvider
from aigcpp_providers.openai_compatible import OpenAICompatibleProvider


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class JsonRepairProvider(ModelProvider):
    name = "json-repair"

    def generate_text(self, messages, *, temperature=0.7, max_tokens=2000, timeout=120):  # type: ignore[no-untyped-def]
        return "prefix {\"ok\": true, \"value\": 3} suffix"


class ProviderTest(unittest.TestCase):
    def test_openai_compatible_provider_posts_chat_completion(self) -> None:
        provider = OpenAICompatibleProvider(base_url="https://api.example/v1", model="demo-model", api_key="token")
        captured = {}

        def fake_urlopen(request, timeout=120):  # type: ignore[no-untyped-def]
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["auth"] = request.headers.get("Authorization")
            return FakeResponse({"choices": [{"message": {"content": "done"}}]})

        with patch("urllib.request.urlopen", fake_urlopen):
            text = provider.generate_text([{"role": "user", "content": "go"}])

        self.assertEqual("done", text)
        self.assertEqual("https://api.example/v1/chat/completions", captured["url"])
        self.assertEqual("demo-model", captured["body"]["model"])
        self.assertEqual("Bearer token", captured["auth"])

    def test_ollama_provider_posts_chat(self) -> None:
        provider = OllamaProvider(base_url="https://ollama.example", model="demo-model")
        captured = {}

        def fake_urlopen(request, timeout=120):  # type: ignore[no-untyped-def]
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse({"message": {"content": "done"}})

        with patch("urllib.request.urlopen", fake_urlopen):
            text = provider.generate_text([{"role": "user", "content": "go"}])

        self.assertEqual("done", text)
        self.assertEqual("https://ollama.example/api/chat", captured["url"])
        self.assertEqual("demo-model", captured["body"]["model"])
        self.assertFalse(captured["body"]["stream"])

    def test_generate_json_extracts_object(self) -> None:
        data = JsonRepairProvider().generate_json([{"role": "user", "content": "go"}])
        self.assertEqual({"ok": True, "value": 3}, data)


if __name__ == "__main__":
    unittest.main()
