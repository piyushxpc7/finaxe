import os
from enum import Enum


class ProviderType(str, Enum):
    MOCK = "mock"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", ProviderType.MOCK).lower()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://user:password@localhost/llm_db"
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "86400"))  # 24 hours default
