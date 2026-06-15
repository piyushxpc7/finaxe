import pytest

from app.llm.cost import compute_cost_usd


class TestCostCalculator:
    """Test cost calculation."""

    def test_compute_cost_openai_gpt4o(self):
        """Test OpenAI GPT-4o pricing."""
        cost = compute_cost_usd("openai", "gpt-4o", 1_000_000, 500_000)
        assert cost == 15.0

    def test_compute_cost_openai_mini(self):
        """Test OpenAI GPT-4o-mini pricing."""
        cost = compute_cost_usd("openai", "gpt-4o-mini", 500_000, 250_000)
        assert abs(cost - 0.225) < 0.01

    def test_compute_cost_anthropic_sonnet(self):
        """Test Anthropic Claude Sonnet pricing."""
        cost = compute_cost_usd("anthropic", "claude-sonnet", 1_000_000, 1_000_000)
        assert cost == 18.0

    def test_compute_cost_anthropic_haiku(self):
        """Test Anthropic Claude Haiku pricing."""
        cost = compute_cost_usd("anthropic", "claude-haiku", 1_000_000, 1_000_000)
        assert cost == 4.8

    def test_compute_cost_mock(self):
        """Test mock provider (free)."""
        cost = compute_cost_usd("mock", "mock-model", 1_000_000, 1_000_000)
        assert cost == 0.0

    def test_compute_cost_unknown_provider(self):
        """Test error handling for unknown provider."""
        with pytest.raises(KeyError, match="Provider 'unknown'"):
            compute_cost_usd("unknown", "model", 100, 100)

    def test_compute_cost_unknown_model(self):
        """Test error handling for unknown model."""
        with pytest.raises(KeyError, match="Model 'unknown'"):
            compute_cost_usd("openai", "unknown", 100, 100)
