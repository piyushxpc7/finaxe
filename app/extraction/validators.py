from __future__ import annotations


def cross_validate_income_statement(m) -> list[str]:
    """
    Returns warning strings for any consistency violations.
    Empty list = no mechanical problems.

    NOTE: These catch structural failures (unit mismatches, sign errors).
    They do NOT catch semantic hallucinations where all numbers are
    internally consistent but wrong.
    """
    warnings = []

    # 1. Gross profit cannot exceed revenue
    if m.gross_profit is not None and m.gross_profit > m.revenue:
        warnings.append(
            f"gross_profit ({m.gross_profit}) > revenue ({m.revenue}): "
            "impossible — likely reporting unit mismatch"
        )

    # 2. Operating income cannot exceed gross profit
    if (
        m.gross_profit is not None
        and m.operating_income is not None
        and m.operating_income > m.gross_profit
    ):
        warnings.append(
            f"operating_income ({m.operating_income}) > gross_profit ({m.gross_profit}): "
            "impossible without negative operating expenses"
        )

    # 3. Gross margin > 100% is physically impossible
    if m.gross_margin_pct is not None and m.gross_margin_pct > 100:
        warnings.append(
            f"gross_margin_pct={m.gross_margin_pct} exceeds 100%: "
            "check revenue vs gross_profit units"
        )

    # 4. Net income 3× above operating income is suspicious
    if m.operating_income is not None and m.operating_income != 0:
        ratio = abs(m.net_income) / abs(m.operating_income)
        if ratio > 3:
            warnings.append(
                f"net_income ({m.net_income}) is {ratio:.1f}× operating_income "
                f"({m.operating_income}): possible unit mismatch or hallucination"
            )

    # 5. Diluted EPS should be ≤ basic EPS (dilution only reduces EPS)
    if m.eps_basic is not None and m.eps_diluted is not None and m.eps_basic != 0:
        ratio = m.eps_diluted / m.eps_basic
        if ratio > 1.05:  # 5% tolerance for rounding
            warnings.append(
                f"eps_diluted ({m.eps_diluted}) > eps_basic ({m.eps_basic}): "
                "dilution cannot increase EPS — fields may be swapped"
            )

    return warnings


def apply_validation_warnings(metrics, warnings: list[str]):
    """Downgrade confidence and append warnings to notes field."""
    if not warnings:
        return metrics
    if metrics.extraction_confidence == "high":
        metrics.extraction_confidence = "medium"
    existing = metrics.notes or ""
    combined = (existing + " | " if existing else "") + "; ".join(warnings)
    metrics.notes = combined[:200]
    return metrics
