from typing import Any

from app.llm.provider import LLMProvider


class AnthropicProvider(LLMProvider):
    """Anthropic LLM provider stub."""

    provider_name = "anthropic"
    model_name = "claude-sonnet"

    async def _generate_impl(self, prompt: str, **kwargs: Any) -> "LLMResponse":
        """Not implemented yet."""
        raise NotImplementedError("Anthropic provider not implemented")

    async def _call_api(self, **kwargs: Any) -> dict[str, Any]:
        """Not implemented yet."""
        raise NotImplementedError("Anthropic provider not implemented")
