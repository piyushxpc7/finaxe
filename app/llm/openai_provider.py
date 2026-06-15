from typing import Any

from app.llm.provider import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider stub."""

    provider_name = "openai"
    model_name = "gpt-4o"

    async def _generate_impl(self, prompt: str, **kwargs: Any) -> "LLMResponse":
        """Not implemented yet."""
        raise NotImplementedError("OpenAI provider not implemented")

    async def _call_api(self, **kwargs: Any) -> dict[str, Any]:
        """Not implemented yet."""
        raise NotImplementedError("OpenAI provider not implemented")
