from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.prompts.registry import load_prompt

SUMMARY_PROMPT_VERSION = "v1"
SUMMARY_MODEL = "gpt-4o-mini"  # 16x cheaper than gpt-4o, adequate for summarization


def build_summary_chain(
    model: str = SUMMARY_MODEL,
    prompt_version: str = SUMMARY_PROMPT_VERSION,
):
    """
    Build the filing section summary chain.

    Input dict: {ticker, section_name, section_text}
    Output: str (5-bullet analyst summary)
    """
    spec = load_prompt("summarize", prompt_version)

    # Pure LCEL: prompt template → LLM → string parser
    prompt = ChatPromptTemplate.from_messages([
        ("system", spec.system),
        ("user", spec.user),
    ])

    llm = ChatOpenAI(model=model, temperature=0)

    return prompt | llm | StrOutputParser()
