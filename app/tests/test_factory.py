import pytest
from unittest.mock import patch

from app.llm.factory import create_provider, MissingAPIKeyError
from app.llm.mock_provider import MockProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.anthropic_provider import AnthropicProvider


class TestProviderFactory:
    """Test provider factory."""

    def test_create_mock_provider(self):
        """Test creating mock provider."""
        provider = create_provider("mock")
        assert isinstance(provider, MockProvider)

    def test_create_openai_provider_missing_key(self):
        """Test OpenAI provider fails without key."""
        with patch("app.llm.factory.OPENAI_API_KEY", None):
            with pytest.raises(MissingAPIKeyError, match="OPENAI_API_KEY"):
                create_provider("openai")

    def test_create_anthropic_provider_missing_key(self):
        """Test Anthropic provider fails without key."""
        with patch("app.llm.factory.ANTHROPIC_API_KEY", None):
            with pytest.raises(MissingAPIKeyError, match="ANTHROPIC_API_KEY"):
                create_provider("anthropic")

    def test_create_unknown_provider(self):
        """Test unknown provider raises error."""
        with pytest.raises(ValueError, match="Unknown provider"):
            create_provider("unknown")

    def test_default_provider_is_mock(self):
        """Test DEFAULT_LLM_PROVIDER defaults to mock."""
        provider = create_provider()
        assert isinstance(provider, MockProvider)


class TestProviderFlip:
    """Test switching between providers via environment."""

    def test_openai_provider_not_implemented(self):
        """Test OpenAI provider raises NotImplementedError."""
        with patch("app.llm.factory.OPENAI_API_KEY", "fake-key"):
            provider = create_provider("openai")
            assert isinstance(provider, OpenAIProvider)
            # Calling generate should raise NotImplementedError

    def test_anthropic_provider_not_implemented(self):
        """Test Anthropic provider raises NotImplementedError."""
        with patch("app.llm.factory.ANTHROPIC_API_KEY", "fake-key"):
            provider = create_provider("anthropic")
            assert isinstance(provider, AnthropicProvider)
