"""Section ranking using LLM-based relevance scoring."""
import json
import logging
import re
from typing import NamedTuple

import openai

logger = logging.getLogger(__name__)


class Section(NamedTuple):
    """A ranked section of filing text."""
    name: str
    content: str
    score: float
    tokens: int


def split_sections(text: str) -> list[tuple[str, str]]:
    """Split filing text into sections based on headings."""
    # Split on common heading patterns
    pattern = r"(?:^|\n)([A-Z][A-Za-z\s&]+?)\n(?:---+|===+|\n)"
    sections = re.split(pattern, text)

    results = []
    for i in range(1, len(sections), 2):
        if i + 1 < len(sections):
            heading = sections[i].strip()
            content = sections[i + 1].strip()
            if len(content) > 100:  # Only keep substantial sections
                results.append((heading, content))

    # If split failed, treat whole text as one section
    if not results:
        results = [("Filing Text", text)]

    return results


async def score_sections_with_llm(
    sections: list[tuple[str, str]],
    task: str = "Extract income statement metrics (revenue, net income, etc.)",
) -> dict[str, float]:
    """
    Use LLM to score section relevance to the extraction task.

    Args:
        sections: List of (heading, content_preview) tuples
        task: Description of what we're extracting

    Returns:
        Dict mapping section names to relevance scores (0-100)
    """
    # Create preview of sections (first 300 chars of each)
    section_previews = [
        f"- {heading}: {content[:300]}..." for heading, content in sections
    ]
    sections_text = "\n".join(section_previews)

    prompt = f"""You are a financial analyst evaluating SEC filing sections for relevance.

Task: {task}

Sections in this filing:
{sections_text}

For each section, score its relevance to the task on a scale of 0-100:
- 90-100: Essential (directly contains needed metrics)
- 70-89: High (provides context/support for main metrics)
- 40-69: Medium (tangential but potentially useful)
- 0-39: Low (tangential or irrelevant)

Return ONLY a JSON object with section names as keys and scores (0-100) as values.
Example: {{"Income Statement": 95, "Risk Factors": 15}}
No other text."""

    try:
        client = openai.AsyncOpenAI()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",  # Use cheaper model for ranking
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )

        response_text = response.choices[0].message.content
        if response_text is None:
            raise ValueError("Empty response from LLM")
        scores = json.loads(response_text.strip())

        logger.info(f"LLM rankings: {scores}")
        return scores

    except Exception as e:
        logger.warning(f"LLM ranking failed: {e}; using fallback heuristics")
        # Fallback: simple heuristics if LLM ranking fails
        return _fallback_scores(sections)


def _fallback_scores(sections: list[tuple[str, str]]) -> dict[str, float]:
    """Fallback scoring using simple pattern matching."""
    scores = {}

    for heading, _content in sections:
        score = 50.0  # Default medium score

        # Income/earnings statements
        if any(term in heading.lower() for term in ["income", "operations", "earnings"]):
            score = 95
        # Balance sheet
        elif any(term in heading.lower() for term in ["balance sheet", "assets", "liabilities"]):
            score = 90
        # Cash flow
        elif "cash flow" in heading.lower():
            score = 85
        # Summary/highlights
        elif any(term in heading.lower() for term in ["summary", "highlights", "overview"]):
            score = 70
        # MD&A
        elif "management" in heading.lower() or "discussion" in heading.lower():
            score = 50
        # Risk/footnotes/other
        elif any(term in heading.lower() for term in ["risk", "note", "footnote"]):
            score = 20
        else:
            score = 30

        scores[heading] = score

    return scores


async def rank_sections(
    text: str, task: str = "Extract financial metrics (revenue, net income, etc.)", model: str = "gpt-4o"
) -> list[Section]:
    """
    Rank sections of filing text by LLM-evaluated relevance to task.

    Args:
        text: Raw filing text
        task: Description of extraction task (used for relevance evaluation)
        model: Model name (for token counting)

    Returns:
        Sections sorted by score (highest first)
    """
    from app.llm.tokenizer import count_tokens

    sections = split_sections(text)

    # Get LLM-based relevance scores
    scores = await score_sections_with_llm(sections, task)

    # Create scored sections
    scored = []
    for heading, content in sections:
        score = scores.get(heading, 30)
        tokens = count_tokens(content, model)
        scored.append(Section(name=heading, content=content, score=score, tokens=tokens))

    # Sort by score descending
    scored.sort(key=lambda s: s.score, reverse=True)

    logger.info(
        f"Ranked {len(scored)} sections: "
        f"{', '.join(f'{s.name}({s.score:.0f})' for s in scored[:5])}"
    )

    return scored


def select_sections_within_budget(
    sections: list[Section], token_budget: int
) -> list[Section]:
    """
    Select highest-scoring sections that fit within token budget.

    Keeps sections whole (never splits) and maintains original order.
    """
    selected = []
    total_tokens = 0

    # Select sections in score order
    for section in sections:
        if total_tokens + section.tokens <= token_budget:
            selected.append(section)
            total_tokens += section.tokens
        else:
            logger.debug(
                f"Budget exceeded: {total_tokens + section.tokens} > {token_budget}; "
                f"dropping '{section.name}' ({section.tokens} tokens)"
            )

    # Restore original document order
    selected_names = {s.name for s in selected}
    ordered = [s for s in sections if s.name in selected_names]

    logger.info(
        f"Selected {len(selected)}/{len(sections)} sections ({total_tokens} tokens): "
        f"{', '.join(s.name for s in ordered)}"
    )

    return ordered
