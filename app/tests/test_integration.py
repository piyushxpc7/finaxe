import asyncio
import pytest

from app.llm.mock_provider import MockProvider
from app.llm.schemas import LLMResponse


class TestGenerateFlow:
    """Test the complete generate flow."""

    @pytest.mark.asyncio
    async def test_generate_returns_response(self):
        """Test generate returns LLMResponse."""
        provider = MockProvider()
        response = await provider.generate("What is AI?", purpose="test")

        assert isinstance(response, LLMResponse)
        assert response.text
        assert response.input_tokens > 0
        assert response.output_tokens > 0
        assert response.provider == "mock"
        assert response.model == "mock-model"
        assert response.finish_reason == "stop"
        assert response.request_id

    @pytest.mark.asyncio
    async def test_generate_latency_recorded(self):
        """Test that latency is recorded in response."""
        provider = MockProvider()
        response = await provider.generate("Test", purpose="test")

        assert isinstance(response.latency_ms, int)

    @pytest.mark.asyncio
    async def test_generate_with_purpose(self):
        """Test generate with specific purpose."""
        provider = MockProvider()
        response = await provider.generate(
            "Extract entities",
            purpose="extraction",
        )

        assert response.text

    @pytest.mark.asyncio
    async def test_generate_flow_integration(self):
        """Test complete flow: API call → cost → ledger → response."""
        provider = MockProvider()

        response = await provider.generate(
            prompt="Test prompt",
            purpose="test",
        )

        assert response.text == "Mock response generated successfully."
        assert response.input_tokens == 100
        assert response.output_tokens == 50
        assert response.provider == "mock"
        assert response.model == "mock-model"


def test_generate_runs_in_event_loop():
    """Test that async generate works in event loop."""
    async def run_test():
        provider = MockProvider()
        response = await provider.generate("Test")
        return response

    response = asyncio.run(run_test())
    assert isinstance(response, LLMResponse)
