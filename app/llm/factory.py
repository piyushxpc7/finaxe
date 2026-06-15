from typing import Literal

from app.config import ANTHROPIC_API_KEY, OPENAI_API_KEY, DEFAULT_LLM_PROVIDER, ProviderType
from app.llm.provider import LLMProvider


class MissingAPIKeyError(Exception):
    """Raised when a provider's API key is missing."""

    pass


def create_provider(
    provider: Literal["mock", "openai", "anthropic"] = DEFAULT_LLM_PROVIDER,
) -> LLMProvider:
    """
    Factory function to create an LLM provider instance.

    Args:
        provider: The provider type to instantiate

    Returns:
        An LLMProvider instance

    Raises:
        MissingAPIKeyError: If API keys are required but missing
        ValueError: If provider is unknown
    """
    if provider == ProviderType.MOCK or provider == "mock":
        from app.llm.mock_provider import MockProvider

        return MockProvider()

    elif provider == ProviderType.OPENAI or provider == "openai":
        if not OPENAI_API_KEY:
            raise MissingAPIKeyError("OPENAI_API_KEY environment variable not set")
        from app.llm.openai_provider import OpenAIProvider

        return OpenAIProvider()

    elif provider == ProviderType.ANTHROPIC or provider == "anthropic":
        if not ANTHROPIC_API_KEY:
            raise MissingAPIKeyError("ANTHROPIC_API_KEY environment variable not set")
        from app.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider()

    else:
        raise ValueError(f"Unknown provider: {provider}")
