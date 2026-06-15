from langchain_core.runnables import RunnableParallel

from app.chains.extraction import build_extraction_chain
from app.chains.summarize import build_summary_chain


def build_research_chain():
    """
    Run extraction and summarization in parallel.

    Input dict: {ticker, fiscal_year, period_type, section_text, section_name, period_str,
                 fiscal_quarter (optional), db (optional)}
    Output: {"metrics": IncomeStatementMetrics, "summary": str}

    Total latency: max(extraction_time, summary_time) instead of sum.
    """
    return RunnableParallel(
        metrics=build_extraction_chain(),
        summary=build_summary_chain(),
    )
