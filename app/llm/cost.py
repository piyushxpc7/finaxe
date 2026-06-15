PRICING = {
    "mock": {
        "mock-model": {
            "input": 0.0,
            "output": 0.0,
        },
    },
    "openai": {
        "gpt-4o": {
            "input": 5.0,
            "output": 20.0,
        },
        "gpt-4o-mini": {
            "input": 0.15,
            "output": 0.60,
        },
    },
    "anthropic": {
        "claude-sonnet": {
            "input": 3.0,
            "output": 15.0,
        },
        "claude-haiku": {
            "input": 0.80,
            "output": 4.0,
        },
    },
}


def compute_cost_usd(provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Compute the cost in USD for an LLM API call.

    Args:
        provider: The LLM provider (e.g., 'openai')
        model: The model name (e.g., 'gpt-4o')
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Cost in USD

    Raises:
        KeyError: If provider or model is not found in the pricing table
    """
    if provider not in PRICING:
        raise KeyError(f"Provider '{provider}' not found in pricing table")

    if model not in PRICING[provider]:
        raise KeyError(f"Model '{model}' not found for provider '{provider}'")

    pricing = PRICING[provider][model]
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    return input_cost + output_cost
