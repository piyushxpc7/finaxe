from enum import Enum
from dataclasses import dataclass


class LLMPurpose(str, Enum):
    EXTRACTION = "extraction"
    SUMMARY = "summary"
    RETRIEVAL = "retrieval"
    AGENT = "agent"


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    provider: str
    model: str
    finish_reason: str
    request_id: str
