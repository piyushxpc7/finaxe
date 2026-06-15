import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional, TYPE_CHECKING
from uuid import uuid4

from app.llm.cost import compute_cost_usd

if TYPE_CHECKING:
    from app.llm.schemas import LLMResponse
else:
    LLMResponse = Any

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    async def generate(self, prompt: str, purpose: Optional[str] = None, **kwargs: Any) -> "LLMResponse":
        """
        Generate a response from the LLM.

        Orchestrates the full flow: API call → cost calculation → ledger write.

        Args:
            prompt: The input prompt
            purpose: The purpose of the call (extraction, summary, etc.)
            **kwargs: Additional provider-specific arguments

        Returns:
            An LLMResponse with tokens, latency, and cost
        """
        start_time = time.time()
        try:
            response = await self._generate_impl(prompt=prompt, **kwargs)
            latency_ms = int((time.time() - start_time) * 1000)

            cost_usd = compute_cost_usd(
                provider=response.provider,
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
            )

            await self._write_ledger_row(
                provider=response.provider,
                model=response.model,
                purpose=purpose,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                finish_reason=response.finish_reason,
                success=True,
            )

            return response
        except Exception:
            latency_ms = int((time.time() - start_time) * 1000)
            await self._write_ledger_row(
                provider=getattr(self, "provider_name", "unknown"),
                model=getattr(self, "model_name", "unknown"),
                purpose=purpose,
                latency_ms=latency_ms,
                success=False,
            )
            raise

    @abstractmethod
    async def _generate_impl(self, prompt: str, **kwargs: Any) -> "LLMResponse":
        """
        Implementation-specific generation logic.

        Subclasses must implement this to return an LLMResponse.

        Args:
            prompt: The input prompt
            **kwargs: Provider-specific parameters

        Returns:
            An LLMResponse
        """
        pass

    @abstractmethod
    async def _call_api(self, **kwargs: Any) -> Any:
        """
        Call the provider's API.

        Args:
            **kwargs: Provider-specific API parameters

        Returns:
            The raw API response
        """
        pass

    async def _write_ledger_row(
        self,
        provider: str,
        model: str,
        purpose: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        cost_usd: Optional[float] = None,
        latency_ms: Optional[int] = None,
        finish_reason: Optional[str] = None,
        success: Optional[bool] = None,
    ) -> None:
        """
        Write an LLM call record to the ledger.

        Ledger failures are logged but never propagated—they must not kill requests.

        Args:
            provider: The LLM provider name
            model: The model used
            purpose: The purpose/intent of the call
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost_usd: Cost in USD
            latency_ms: Latency in milliseconds
            finish_reason: API finish reason (e.g., 'stop', 'length')
            success: Whether the call succeeded
        """
        try:
            from sqlalchemy import insert
            from sqlalchemy.ext.asyncio import AsyncSession

            from app.db.models import LLMCall

            async with AsyncSession() as session:
                stmt = insert(LLMCall).values(
                    id=uuid4(),
                    ts=datetime.now(timezone.utc),
                    provider=provider,
                    model=model,
                    purpose=purpose,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost_usd,
                    latency_ms=latency_ms,
                    finish_reason=finish_reason,
                    success=success,
                )
                await session.execute(stmt)
                await session.commit()
        except Exception:
            logger.exception("Failed to write LLM call ledger row")
