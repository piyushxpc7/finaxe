from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
import re

INCOME_STATEMENT_SCHEMA_VERSION = "v1.0"


class SegmentRevenue(BaseModel):
    segment_name: str = Field(description="Segment name as stated in the filing.")
    revenue_millions: float = Field(description="Segment revenue in millions USD.", gt=0)
    yoy_growth_pct: Optional[float] = Field(
        default=None,
        description="YoY growth percentage (e.g., 12.5 = 12.5%). Null if not stated.",
    )


class IncomeStatementMetrics(BaseModel):

    # Identity
    ticker: str = Field(description="Stock ticker symbol, uppercase. E.g. 'AAPL'.")
    company_name: str = Field(description="Full legal company name as in the filing.")
    fiscal_year: int = Field(description="4-digit fiscal year.", ge=1990, le=2030)
    fiscal_quarter: Optional[Literal["Q1", "Q2", "Q3", "Q4"]] = Field(
        default=None,
        description="Quarter for 10-Q filings. Null for annual 10-K.",
    )
    period_type: Literal["annual", "quarterly"] = Field(
        description="'annual' for 10-K, 'quarterly' for 10-Q."
    )
    reporting_unit: Literal["millions", "thousands", "billions"] = Field(
        default="millions",
        description="Unit the company reports in. Most large-caps use millions.",
    )

    # Income statement
    revenue: float = Field(description="Total net revenue in the reporting unit.", gt=0)
    gross_profit: Optional[float] = Field(
        default=None,
        description="Revenue minus COGS, in the reporting unit.",
    )
    operating_income: Optional[float] = Field(
        default=None,
        description="Operating income (EBIT) in the reporting unit. Can be negative.",
    )
    net_income: float = Field(
        description="Net income attributable to common shareholders. Can be negative."
    )
    ebitda: Optional[float] = Field(
        default=None,
        description="EBITDA if explicitly stated. Do NOT calculate — extract only.",
    )
    eps_basic: Optional[float] = Field(
        default=None, description="Basic EPS. Can be negative."
    )
    eps_diluted: Optional[float] = Field(
        default=None, description="Diluted EPS. Can be negative."
    )

    # Margins
    gross_margin_pct: Optional[float] = Field(
        default=None,
        description="Gross margin %. E.g., 43.2 for 43.2%. Compute from gross_profit/revenue if available.",
    )
    operating_margin_pct: Optional[float] = Field(
        default=None,
        description="Operating margin %. Compute if not stated.",
    )
    net_margin_pct: Optional[float] = Field(
        default=None,
        description="Net margin %. Compute from net_income/revenue.",
    )

    # Segment breakdown
    segments: Optional[list[SegmentRevenue]] = Field(
        default=None,
        description="Revenue by segment if stated. Null if no segment breakdown.",
    )

    # Trust metadata
    extraction_confidence: Literal["high", "medium", "low"] = Field(
        description=(
            "'high': all values directly stated in text. "
            "'medium': some values computed from stated numbers. "
            "'low': values ambiguous or inference required."
        )
    )
    notes: Optional[str] = Field(
        default=None,
        description="Caveats or ambiguities. Max 200 chars.",
        max_length=200,
    )
    schema_version: str = Field(default=INCOME_STATEMENT_SCHEMA_VERSION)

    # ── Field validators ──────────────────────────────────────────────────────

    @field_validator(
        "revenue", "gross_profit", "operating_income", "net_income", "ebitda",
        mode="before",
    )
    @classmethod
    def clean_financial_number(cls, v):
        """
        Normalises LLM number formatting:
          "3,218.4"  → 3218.4
          "$3,218.4" → 3218.4
          "(1,234)"  → -1234.0   (accounting negatives)
        """
        if isinstance(v, (int, float)):
            return v
        if isinstance(v, str):
            s = v.strip()
            negative = s.startswith("(") and s.endswith(")")
            s = re.sub(r"[$()\s,]", "", s)
            try:
                result = float(s)
                return -result if negative else result
            except ValueError:
                raise ValueError(f"Cannot parse as number: '{v}'")
        return v

    @field_validator("ticker")
    @classmethod
    def ticker_uppercase(cls, v):
        return v.upper().strip()

    # ── Model validators ──────────────────────────────────────────────────────

    @model_validator(mode="after")
    def compute_missing_margins(self):
        """Derive margins from stated components if not provided."""
        if self.gross_margin_pct is None and self.gross_profit is not None and self.revenue > 0:
            self.gross_margin_pct = round(100 * self.gross_profit / self.revenue, 2)
        if self.operating_margin_pct is None and self.operating_income is not None and self.revenue > 0:
            self.operating_margin_pct = round(100 * self.operating_income / self.revenue, 2)
        if self.net_margin_pct is None and self.revenue > 0:
            self.net_margin_pct = round(100 * self.net_income / self.revenue, 2)
        return self

    @model_validator(mode="after")
    def sanity_check(self):
        """Catch physically impossible values — triggers Instructor retry."""
        if self.gross_margin_pct is not None and self.gross_margin_pct > 100:
            raise ValueError(
                f"gross_margin_pct={self.gross_margin_pct} exceeds 100% — "
                "check reporting unit mismatch."
            )
        return self
