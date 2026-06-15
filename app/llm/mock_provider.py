from typing import Any
from uuid import uuid4

from app.llm.provider import LLMProvider
from app.llm.schemas import LLMResponse


class MockProvider(LLMProvider):
    """Mock LLM provider for testing and development."""

    provider_name = "mock"
    model_name = "mock-model"

    async def _generate_impl(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """
        Generate a mock response without calling any API.

        Args:
            prompt: The input prompt (ignored for mock)
            **kwargs: Additional arguments (ignored for mock)

        Returns:
            A mock LLMResponse
        """
        response = await self._call_api(prompt=prompt, **kwargs)

        return LLMResponse(
            text=response["text"],
            input_tokens=response["input_tokens"],
            output_tokens=response["output_tokens"],
            latency_ms=0,
            provider="mock",
            model="mock-model",
            finish_reason="stop",
            request_id=str(uuid4()),
        )

    async def _call_api(self, **kwargs: Any) -> dict[str, Any]:
        """
        Simulate an API call with mock data.

        Returns:
            A mock response dictionary
        """
        return {
            "text": "Mock response generated successfully.",
            "input_tokens": 100,
            "output_tokens": 50,
        }
