from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import NUMERIC, Boolean, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column


class LLMCall:
    """ORM model for LLM API call ledger."""

    __tablename__ = "llm_calls"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    ts: Mapped[datetime] = mapped_column(default=func.now())
    provider: Mapped[Optional[str]] = mapped_column(Text)
    model: Mapped[Optional[str]] = mapped_column(Text)
    purpose: Mapped[Optional[str]] = mapped_column(Text)
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    cost_usd: Mapped[Optional[float]] = mapped_column(NUMERIC)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    finish_reason: Mapped[Optional[str]] = mapped_column(Text)
    success: Mapped[Optional[bool]] = mapped_column(Boolean)
    prompt_version: Mapped[Optional[str]] = mapped_column(Text)
