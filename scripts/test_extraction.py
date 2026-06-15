import asyncio
import logging
from app.extraction.financial import extract_income_statement

logging.basicConfig(level=logging.INFO)

# Paste a few paragraphs from AAPL's 10-K Item 8 here
AAPL_EXCERPT = """
Apple Inc.
CONSOLIDATED STATEMENTS OF OPERATIONS
(In millions, except number of shares which are reflected in thousands and per share amounts)

Years ended
                                    September 30, 2023   September 24, 2022
Net sales:
  Products                          $   298,085          $   316,199
  Services                               85,200               78,129
Total net sales                         383,285              394,328

Cost of sales:
  Products                              189,282              201,471
  Services                               24,855               22,075
Total cost of sales                     214,137              223,546

Gross margin                            169,148              170,782

Operating expenses:
  Research and development               29,915               26,251
  Selling, general and administrative    24,932               25,094
Total operating expenses                 54,847               51,345

Operating income                        114,301              119,437

Other income/(expense), net                 (565)               (334)
Income before provision for income taxes 113,736              119,103
Provision for income taxes                29,749               19,300
Net income                             $  96,995            $  99,803

Earnings per share:
  Basic                               $    6.16            $    6.15
  Diluted                             $    6.13            $    6.11
"""

async def main():
    metrics, meta = await extract_income_statement(
        ticker="AAPL",
        fiscal_year=2023,
        period_type="annual",
        section_text=AAPL_EXCERPT,
        model="gpt-4o-mini",
        db=None,  # no DB yet — just test the extraction
    )

    print("\n=== Extracted ===")
    print(f"Ticker:            {metrics.ticker}")
    print(f"Revenue:           {metrics.revenue:,.1f} {metrics.reporting_unit}")
    print(f"Gross Profit:      {metrics.gross_profit:,.1f}")
    print(f"Operating Income:  {metrics.operating_income:,.1f}")
    print(f"Net Income:        {metrics.net_income:,.1f}")
    print(f"EPS Diluted:       {metrics.eps_diluted}")
    print(f"Gross Margin:      {metrics.gross_margin_pct:.2f}%")
    print(f"Net Margin:        {metrics.net_margin_pct:.2f}%")
    print(f"Confidence:        {metrics.extraction_confidence}")

    print("\n=== Metadata ===")
    print(f"Model:             {meta['model']}")
    print(f"Input tokens:      {meta['input_tokens']}")
    print(f"Output tokens:     {meta['output_tokens']}")
    print(f"Cost USD:          {meta['cost_usd']}")
    print(f"Warnings:          {meta['validation_warnings']}")

asyncio.run(main())
