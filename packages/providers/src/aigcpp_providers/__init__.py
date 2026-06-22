"""Model provider adapters for AIGC PP Workflow."""

from .base import ModelProvider, ProviderError
from .fake import FakeProvider
from .ollama import OllamaProvider
from .openai_compatible import OpenAICompatibleProvider

__all__ = [
    "FakeProvider",
    "ModelProvider",
    "OllamaProvider",
    "OpenAICompatibleProvider",
    "ProviderError",
    "build_provider",
]


def build_provider(
    provider: str,
    *,
    base_url: str = "",
    model: str = "",
    api_key: str = "",
) -> ModelProvider:
    normalized = provider.strip().lower()
    if normalized in {"fake", "test"}:
        return FakeProvider(model=model or "fake-model")
    if normalized in {"openai-compatible", "openai_compatible", "openai"}:
        return OpenAICompatibleProvider(base_url=base_url, model=model, api_key=api_key)
    if normalized == "ollama":
        return OllamaProvider(base_url=base_url, model=model)
    raise ProviderError(f"unsupported provider: {provider}")
