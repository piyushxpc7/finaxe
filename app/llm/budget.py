"""Context budget management for large filings."""
import logging
from typing import Optional

from app.llm.tokenizer import count_tokens, count_message_tokens
from app.llm.ranker import rank_sections, select_sections_within_budget

logger = logging.getLogger(__name__)


class ContextBudget:
    """Manage context window budget for LLM requests."""

    # Token limits for common models
    MODEL_LIMITS = {
        "gpt-4o": 128000,
        "gpt-4-turbo": 128000,
        "gpt-4": 8192,
        "gpt-3.5-turbo": 4096,
    }

    # Reserve tokens for response and overhead
    RESPONSE_RESERVE = 2000
    OVERHEAD_RESERVE = 500

    def __init__(self, model: str = "gpt-4o", reserve_tokens: int = 2500):
        """Initialize budget manager.

        Args:
            model: Model name (used to get token limit)
            reserve_tokens: Tokens to reserve for response + overhead
        """
        self.model = model
        self.total_limit = self.MODEL_LIMITS.get(model, 128000)
        self.reserve = reserve_tokens
        self.available = self.total_limit - self.reserve

    def calculate_content_budget(
        self,
        system_msg: str,
        user_prompt_template: str,
        ticker: str = "",
        period_str: str = "",
        period_type: str = "",
    ) -> int:
        """Calculate how many tokens are available for filing text.

        Args:
            system_msg: System prompt
            user_prompt_template: User prompt with placeholders
            ticker: Ticker symbol
            period_str: Period string (e.g., "FY2023")
            period_type: Period type (e.g., "annual")

        Returns:
            Tokens available for filing content
        """
        # Fill template to estimate size
        user_msg = user_prompt_template.format(
            ticker=ticker or "TICKER",
            period_str=period_str or "FY2024",
            period_type=period_type or "annual",
            section_text="[CONTENT_PLACEHOLDER]",
        )

        # Count tokens for fixed parts
        system_tokens = count_tokens(system_msg, self.model)
        user_base_tokens = count_tokens(user_msg.replace("[CONTENT_PLACEHOLDER]", ""), self.model)

        fixed_tokens = system_tokens + user_base_tokens + 50  # +50 for message overhead

        logger.debug(
            f"Fixed tokens: {fixed_tokens} (system: {system_tokens}, user: {user_base_tokens})"
        )

        content_budget = self.available - fixed_tokens
        if content_budget < 0:
            logger.warning(f"Insufficient budget! Fixed tokens ({fixed_tokens}) exceed available ({self.available})")
            content_budget = 0

        logger.info(f"Content budget: {content_budget} tokens (out of {self.total_limit} limit)")
        return content_budget

    async def budget_section_text(
        self,
        text: str,
        system_msg: str,
        user_prompt_template: str,
        ticker: str = "",
        period_str: str = "",
        period_type: str = "",
        task: str = "Extract financial metrics (revenue, net income, assets, liabilities)",
    ) -> str:
        """Fit filing text within context budget by ranking and selecting sections.

        Args:
            text: Raw filing text (may be very large)
            system_msg: System prompt
            user_prompt_template: User message template
            ticker: Ticker symbol
            period_str: Period string
            period_type: Period type
            task: Description of extraction task (for LLM-based ranking)

        Returns:
            Budgeted text (whole sections kept intact)
        """
        # Calculate budget
        content_budget = self.calculate_content_budget(
            system_msg, user_prompt_template, ticker, period_str, period_type
        )

        # Check if text already fits
        original_tokens = count_tokens(text, self.model)
        if original_tokens <= content_budget:
            logger.info(f"Text fits budget ({original_tokens} <= {content_budget})")
            return text

        # Budget exceeded: rank (with LLM) and select sections
        logger.warning(
            f"Text exceeds budget ({original_tokens} > {content_budget}); "
            "ranking sections with LLM to fit..."
        )

        sections = await rank_sections(text, task, self.model)
        selected = select_sections_within_budget(sections, content_budget)

        # Reconstruct text in original order
        budgeted_text = "\n\n".join(s.content for s in selected)
        final_tokens = count_tokens(budgeted_text, self.model)

        logger.info(
            f"Budgeted text: {final_tokens}/{content_budget} tokens "
            f"({len(selected)}/{len(sections)} sections)"
        )

        return budgeted_text

    def estimate_messages_size(self, messages: list[dict]) -> int:
        """Estimate token count for a message list."""
        return count_message_tokens(messages, self.model)
