"""
Test context budget management with LLM-based ranking.
Run: python scripts/test_budget.py

Demonstrates:
1. LLM-based section ranking by relevance (Income Statement > footnotes)
2. Budget selection keeping sections whole (never split)
3. Large filing text trimmed to fit within token limit
"""
import asyncio
from app.llm.budget import ContextBudget
from app.llm.ranker import rank_sections, select_sections_within_budget, _fallback_scores, split_sections
from app.llm.tokenizer import count_tokens

# Sample filing excerpt with multiple sections
LARGE_FILING = """
CONSOLIDATED BALANCE SHEET
As of December 31, 2023

ASSETS
Current assets:
  Cash and cash equivalents           $ 28,500
  Marketable securities                15,200
  Accounts receivable                   42,300
  Inventory                             38,900
  Prepaid expenses                       5,600
Total current assets                  $ 130,500

Property and equipment:
  Land and buildings                   $ 45,000
  Machinery and equipment               82,000
  Less: accumulated depreciation       (35,000)
Net property and equipment            $ 92,000

Total assets                           $ 222,500

LIABILITIES AND STOCKHOLDERS' EQUITY

Current liabilities:
  Accounts payable                     $ 18,500
  Current portion of debt               10,000
  Accrued expenses                      12,300
Total current liabilities              $ 40,800

Long-term debt                          45,000
Total liabilities                      $ 85,800

Stockholders' equity:
  Common stock                         $ 50,000
  Additional paid-in capital            62,500
  Retained earnings                     24,200
Total stockholders' equity             $ 136,700

Total liabilities and equity           $ 222,500

CONSOLIDATED STATEMENTS OF OPERATIONS
Years ended December 31, 2023 and 2022

                                    2023         2022
Net revenues                      $485,200    $420,100
Cost of goods sold                (291,200)   (252,100)
Gross profit                       $194,000    $168,000

Operating expenses:
  Selling and marketing             (45,000)    (38,000)
  General and administrative        (38,500)    (32,000)
  Research and development          (25,300)    (22,000)
Total operating expenses            (108,800)    (92,000)

Operating income                    $85,200     $76,000

Other income (expense):
  Interest income                     1,500       2,100
  Interest expense                   (3,200)     (2,800)
  Other income                          800         600
Total other income                      (900)        (100)

Income before taxes                 $84,300     $75,900
Income tax expense                  (21,100)    (18,900)
Net income                          $63,200     $57,000

Diluted earnings per share             $3.16       $2.85

MANAGEMENT'S DISCUSSION AND ANALYSIS

This section discusses financial performance for 2023. Net revenues grew 15.5%
year-over-year driven by strong demand in the North American and European markets.
Gross margin improved to 39.9% from 40.0% due to improved manufacturing efficiency
and better product mix. Operating expenses increased $16.8 million due to investments
in R&D and market expansion initiatives.

The company continues to invest in technology infrastructure and has allocated
significant resources to developing next-generation products. Management expects
continued growth in 2024 driven by new product launches and market expansion.

RISK FACTORS

1. Market Risk: The company faces competition from established players and new entrants.
Changes in market conditions could impact growth rates and profitability.

2. Currency Risk: A significant portion of revenue is derived from international
markets, creating exposure to foreign exchange fluctuations.

3. Supply Chain Risk: The company relies on suppliers for critical components.
Disruptions could impact manufacturing and delivery timelines.

4. Regulatory Risk: Changes in environmental, labor, or tax regulations could
increase operating costs.

FOOTNOTES

Note 1: Accounting Policies
The consolidated financial statements have been prepared in accordance with
Generally Accepted Accounting Principles (GAAP).

Note 2: Inventory
Inventory is stated at the lower of cost or market value using the FIFO method.

Note 3: Depreciation
Property and equipment is depreciated using the straight-line method over useful
lives ranging from 5 to 30 years.

Note 4: Commitments and Contingencies
The company has operating leases for office and warehouse space with total
commitments of $2.5 million over the next 5 years.
"""


async def test_section_ranking():
    """Sections are ranked by financial relevance using LLM."""
    sections = await rank_sections(LARGE_FILING, task="Extract income statement metrics")

    # Check that Income Statement and Balance Sheet are top-ranked
    top_names = [s.name for s in sections[:3]]
    print(f"Top 3 sections (LLM-ranked): {top_names}")

    # Income Statement and Balance Sheet should score highest
    assert any("Balance Sheet" in s.name for s in sections[:2]), "Balance Sheet should rank high"
    assert any("Operations" in s.name or "Income" in s.name for s in sections[:2]), "Income Statement should rank high"

    # Management Discussion should rank lower than financial statements
    mgmt_section = next((s for s in sections if "Management" in s.name), None)
    income_section = next((s for s in sections if "Operations" in s.name or "Income" in s.name), None)
    if mgmt_section and income_section:
        assert income_section.score > mgmt_section.score, "Income Statement should rank above MD&A"

    print("✓ Section ranking (LLM-based relevance scoring)")


async def test_budget_selection_keeps_sections_whole():
    """Selected sections are kept whole, never split."""
    sections = await rank_sections(LARGE_FILING)
    total_tokens = sum(s.tokens for s in sections)

    # Set budget at 50% of total
    budget = int(total_tokens * 0.5)
    selected = select_sections_within_budget(sections, budget)

    # Verify sections are kept whole
    selected_tokens = sum(s.tokens for s in selected)
    assert selected_tokens <= budget, "Selected sections should fit budget"

    # Verify no sections are split
    for selected_section in selected:
        for original_section in sections:
            if selected_section.name == original_section.name:
                assert selected_section.tokens == original_section.tokens, "Section should be whole, not split"

    print(f"✓ Budget selection keeps sections whole ({selected_tokens}/{budget} tokens, {len(selected)}/{len(sections)} sections)")


async def test_context_budget_fits_large_filing():
    """Large filing is trimmed to fit within token limit."""
    original_tokens = count_tokens(LARGE_FILING)
    print(f"Original filing: {original_tokens} tokens")

    budget = ContextBudget("gpt-4o")

    # Simulate realistic system/user prompts
    system_msg = """You are a financial data extraction specialist. Extract income statement metrics."""
    user_template = "Extract metrics for {ticker} ({period_str}). Filing:\n\n{section_text}"

    # Apply budget (with LLM-based ranking)
    budgeted_text = await budget.budget_section_text(
        LARGE_FILING,
        system_msg,
        user_template,
        ticker="ACME",
        period_str="FY2023",
        period_type="annual",
        task="Extract income statement metrics (revenue, expenses, net income)",
    )

    budgeted_tokens = count_tokens(budgeted_text)
    content_budget = budget.calculate_content_budget(
        system_msg, user_template, ticker="ACME", period_str="FY2023", period_type="annual"
    )

    assert budgeted_tokens <= content_budget, "Budgeted text should fit content budget"
    assert len(budgeted_text) < len(LARGE_FILING), "Text should be trimmed"
    assert any(term in budgeted_text for term in ["BALANCE SHEET", "OPERATIONS", "INCOME"]), "High-priority sections should be kept"

    print(f"✓ Large filing trimmed: {original_tokens} → {budgeted_tokens} tokens (kept high-priority sections)")


def test_budget_respects_token_limits():
    """Budget respects model token limits."""
    budget = ContextBudget("gpt-4o")

    assert budget.total_limit == 128000, "gpt-4o should have 128k limit"
    assert budget.available < budget.total_limit, "Available should reserve for response"
    assert budget.reserve > 0, "Should reserve tokens for response"

    print(f"✓ Token limits (model: {budget.total_limit}, reserve: {budget.reserve}, available: {budget.available})")


async def run_all_tests():
    """Run all async tests."""
    print("Testing context budget management with LLM-based ranking...\n")
    await test_section_ranking()
    await test_budget_selection_keeps_sections_whole()
    await test_context_budget_fits_large_filing()
    test_budget_respects_token_limits()
    print("\n✓ All budget tests passed")
    print("\nIntegration with extraction chain:")
    print("  1. LLM evaluates section relevance to extraction task")
    print("  2. High-priority sections (Income Statement) kept first")
    print("  3. Sections kept whole (never split mid-table)")
    print("  4. Low-priority sections (Risk Factors) dropped when over budget")
    print("  5. Fallback heuristics if LLM ranking fails")
    print("  6. Cache key includes budgeted text, not original")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
