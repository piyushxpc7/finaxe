"""
Smoke tests for Day 4 implementation.
Run: python scripts/test_day4.py
All assertions should pass before committing.
"""
import asyncio
from app.prompts.registry import load_prompt, list_versions, invalidate_cache

AAPL_EXCERPT = """
Apple Inc.
CONSOLIDATED STATEMENTS OF OPERATIONS
(In millions, except number of shares which are reflected in thousands
and per share amounts)
Years ended September 30,
                                        2023        2022        2021
Net sales                          $ 383,285   $ 394,328   $ 365,817
Cost of sales                        214,137     223,546     212,981
Gross margin                         169,148     170,782     152,836
Operating income                     114,301     119,437     108,949
Net income                          $ 96,995    $ 99,803    $ 94,680

Earnings per share:
Basic                                $  6.16    $  6.15    $  5.67
Diluted                              $  6.13    $  6.11    $  5.61
"""


def test_registry_happy_path():
    """Registry loads a valid prompt."""
    spec = load_prompt("extraction", "v1")
    assert spec.name == "extraction"
    assert spec.version == "v1"
    assert "{ticker}" in spec.user
    assert "{section_text}" in spec.user
    assert len(spec.system) > 100, "System prompt should be substantial"
    print("✓ Registry happy path")


def test_registry_fails_loudly():
    """Registry raises FileNotFoundError on missing version."""
    try:
        load_prompt("extraction", "v999")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError as e:
        assert "v999" in str(e)
        assert "Available" in str(e)
    print("✓ Registry fails loudly on missing version")


def test_list_versions():
    """list_versions returns available versions."""
    versions = list_versions("extraction")
    assert "v1" in versions
    print(f"✓ list_versions: {versions}")


def test_langchain_template_conversion():
    """PromptSpec converts to a LangChain template."""
    spec = load_prompt("extraction", "v1")
    template = spec.to_langchain_template()
    # Template should have the variables from the user message
    assert "ticker" in template.input_variables
    assert "section_text" in template.input_variables
    print("✓ LangChain template conversion")


async def test_research_chain_runs():
    """End-to-end test of the parallel research chain."""
    from app.chains.research import build_research_chain

    chain = build_research_chain()
    result = await chain.ainvoke({
        "ticker":       "AAPL",
        "fiscal_year":  2023,
        "period_type":  "annual",
        "period_str":   "FY2023",
        "section_text": AAPL_EXCERPT,
        "section_name": "Income Statement",
    })

    metrics = result["metrics"]
    summary = result["summary"]

    assert metrics.ticker == "AAPL"
    assert metrics.fiscal_year == 2023
    assert metrics.revenue is not None, "Revenue should be extracted"
    # AAPL FY2023 revenue: $383,285M (in millions)
    assert abs(metrics.revenue - 383285) < 1000, f"Revenue mismatch: {metrics.revenue}"
    assert metrics.net_income is not None
    assert metrics.extraction_confidence in ("high", "medium", "low")

    assert isinstance(summary, str)
    assert len(summary) > 100, "Summary should be substantial"
    assert "•" in summary or "-" in summary or "AAPL" in summary, "Summary should reference AAPL"

    print(f"✓ Research chain complete")
    print(f"  Revenue:    ${metrics.revenue:,.0f}M")
    print(f"  Net income: ${metrics.net_income:,.0f}M")
    print(f"  Confidence: {metrics.extraction_confidence}")
    print(f"  Summary (first 200 chars): {summary[:200]}...")


if __name__ == "__main__":
    test_registry_happy_path()
    test_registry_fails_loudly()
    test_list_versions()
    test_langchain_template_conversion()
    asyncio.run(test_research_chain_runs())
    print("\n✓ All Day 4 smoke tests passed")
