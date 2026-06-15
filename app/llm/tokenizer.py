"""Token counting utilities for context budget management."""
import logging

try:
    import tiktoken
except ImportError:
    tiktoken = None

logger = logging.getLogger(__name__)

# Cache for encoder instances
_encoders = {}


def get_encoder(model: str = "gpt-4o"):
    """Get or create a tiktoken encoder for the model."""
    if tiktoken is None:
        logger.warning("tiktoken not installed; using fallback estimation")
        return None

    if model not in _encoders:
        try:
            _encoders[model] = tiktoken.encoding_for_model(model)
        except Exception as e:
            logger.warning(f"Failed to load encoder for {model}: {e}; using fallback")
            return None

    return _encoders[model]


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Count tokens in text using tiktoken."""
    encoder = get_encoder(model)
    if encoder is None:
        return estimate_tokens(text)

    try:
        return len(encoder.encode(text))
    except Exception as e:
        logger.warning(f"Token count failed: {e}; using fallback")
        return estimate_tokens(text)


def estimate_tokens(text: str) -> int:
    """Fallback: estimate tokens as ~4 chars per token (conservative)."""
    return len(text) // 4


def count_message_tokens(
    messages: list[dict], model: str = "gpt-4o"
) -> int:
    """Count tokens for a list of messages (OpenAI format)."""
    encoder = get_encoder(model)
    if encoder is None:
        return sum(estimate_tokens(m.get("content", "")) for m in messages) + len(messages) * 10

    try:
        total = 0
        for message in messages:
            # Each message adds ~4 tokens (role + metadata)
            total += 4
            total += len(encoder.encode(message.get("content", "")))
        return total
    except Exception as e:
        logger.warning(f"Message token count failed: {e}")
        return sum(estimate_tokens(m.get("content", "")) for m in messages) + len(messages) * 10
