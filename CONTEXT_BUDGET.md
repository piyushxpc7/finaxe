# Context Budget Management

## Overview

Large SEC filings often exceed LLM context windows (e.g., 10-K filings can be 100k+ tokens). The context budget system intelligently **ranks sections by relevance and drops low-priority content whole**, preventing data corruption from naive truncation.

## The Problem

**Bad approach** (naive truncation):
```
Income Statement:
Revenue        $ 383,285
Cost of sales    214,137
Gross margin     169,148
...

→ Truncate at token limit mid-table →

Revenue        $ 383,285
Cost of sales    214,137
Gross [CUTOFF]

Table corrupted. Extraction fails or uses wrong values.
```

**Good approach** (section ranking):
```
Sections (ranked by relevance):
1. Income Statement        (High priority, 2000 tokens)  ← Keep
2. Balance Sheet          (High priority, 1500 tokens)  ← Keep
3. Cash Flow Statement    (High priority, 1200 tokens)  ← Keep
4. Management Discussion  (Medium priority, 800 tokens) ← Keep
5. Risk Factors           (Low priority, 600 tokens)    ← DROP

Total: 5500 tokens (5100 budget) → Select 4 whole sections
Never split. Preserve data integrity.
```

## Architecture

### 1. Token Counting (`app/llm/tokenizer.py`)

Accurate token counting using `tiktoken`:

```python
from app.llm.tokenizer import count_tokens

text = "Extract AAPL FY2023 revenue from filing..."
tokens = count_tokens(text, model="gpt-4o")  # 18 tokens
```

Fallback estimation (~4 chars per token) if tiktoken unavailable.

### 2. Section Ranking (`app/llm/ranker.py`)

**LLM-based relevance scoring** - Uses Claude to evaluate section importance to the task:

```python
task = "Extract income statement metrics (revenue, net income, etc.)"

# LLM evaluates each section
Consolidated Statements of Operations → Score: 95 (Essential)
Consolidated Balance Sheet           → Score: 90 (Essential)
Consolidated Statements of Cash Flows → Score: 85 (High value)
Management's Discussion              → Score: 50 (Context)
Risk Factors                         → Score: 20 (Low priority)
```

**How it works:**
1. Split filing into logical sections (by heading)
2. Call Claude (gpt-4o-mini) with task description
3. LLM returns JSON scores for each section (0-100 scale)
4. Scores used to rank sections for budget selection

**Scoring scale:**
- 90-100: Essential (directly contains needed metrics)
- 70-89: High value (provides context/support)
- 40-69: Medium (tangential but useful)
- 0-39: Low (tangential or irrelevant)

**Fallback:** If LLM ranking fails, use simple heuristics (pattern matching on headings)

### 3. Budget Selection (`app/llm/budget.py`)

Select highest-scoring sections that fit within token budget:

```python
from app.llm.budget import ContextBudget

budget = ContextBudget("gpt-4o")
content_budget = budget.calculate_content_budget(
    system_msg="You are a financial analyst...",
    user_prompt_template="Extract {section_text}...",
    ticker="AAPL",
)
# → 45,000 tokens available for filing content

budgeted_text = budget.budget_section_text(
    raw_filing_text,
    system_msg,
    user_prompt_template,
    ticker="AAPL",
)
# → Large filing trimmed to top-priority sections
```

### 4. Integration (`app/chains/extraction.py`)

Extraction chain now applies budget before API call:

```python
# Before: Pass raw text (may be too large)
user_msg = spec.user.format(
    ticker=ticker,
    section_text=section_text,  # ← Raw, might be 100k+ tokens
)

# After: Apply budget (keep sections whole)
budget = ContextBudget(model)
budgeted_text = budget.budget_section_text(
    section_text,
    spec.system,
    spec.user,
    ticker=ticker,
)
user_msg = spec.user.format(
    ticker=ticker,
    section_text=budgeted_text,  # ← Trimmed to fit budget
)
```

## Design Decisions

| Aspect | Choice | Why |
|--------|--------|-----|
| Ranking | Relevance scores | High-priority sections (Income Statement) kept first |
| Selection | Greedy (highest-score first) | Simple, deterministic |
| Splitting | Never split sections | Preserves data integrity (whole tables, not fragments) |
| Fallback | Estimation (÷4) | Works without tiktoken dependency |
| Token limit | Model-specific | gpt-4o: 128k, gpt-4: 8k (accounts for actual limits) |
| Reserve | 2500 tokens | Response (2k) + overhead (500) |

## Usage

### Basic Example

```python
import asyncio
from app.llm.budget import ContextBudget

async def process_filing():
    # Large filing text
    filing_text = open("10-K.txt").read()  # 200k tokens

    # Create budget
    budget = ContextBudget("gpt-4o")

    # Apply budget (LLM-based ranking)
    budgeted = await budget.budget_section_text(
        filing_text,
        system_prompt,
        user_prompt_template,
        ticker="AAPL",
        period_str="FY2023",
        task="Extract income statement metrics (revenue, expenses, net income)",
    )

    # budgeted is now ~100k tokens (fits 128k limit with reserve)
    # Contains: Income Statement, Balance Sheet, Cash Flow (whole)
    # Dropped: Risk Factors, Management Discussion
    # LLM determined relevance scores based on task description

asyncio.run(process_filing())
```

### Customizing Token Limits

```python
# For different models
budget = ContextBudget("gpt-4-turbo")  # 128k limit
budget = ContextBudget("gpt-4")        # 8k limit

# Custom reserve
budget = ContextBudget("gpt-4o", reserve_tokens=1000)  # Less conservative
```

### Ranking Sections Separately

```python
from app.llm.ranker import rank_sections, select_sections_within_budget
from app.llm.tokenizer import count_tokens

filing_text = open("10-K.txt").read()

# Rank all sections
sections = rank_sections(filing_text)
for s in sections[:5]:
    print(f"{s.name}: score={s.score}, tokens={s.tokens}")
# Income Statement: score=100, tokens=2000
# Balance Sheet: score=90, tokens=1500
# ...

# Select to fit budget
selected = select_sections_within_budget(sections, token_budget=45000)
# → Selected: [Income Statement, Balance Sheet, Cash Flow, MD&A]

# Reconstruct text
budgeted_text = "\n\n".join(s.content for s in selected)
```

## Testing

```bash
make budget
```

Verifies:
- ✓ Section ranking (by financial relevance)
- ✓ Budget selection keeps sections whole (never split)
- ✓ Large filings trimmed to fit within token limit
- ✓ Token limits respected for each model

Example output:
```
Original filing: 125,400 tokens
Content budget: 45,000 tokens

Top 3 sections: Consolidated Statements of Operations, Consolidated Balance Sheet, Consolidated Statements of Cash Flows
Selected 4/12 sections (44,200 tokens): Income Statement, Balance Sheet, Cash Flow, MD&A
✓ Large filing trimmed: 125,400 → 44,200 tokens
```

## Cost Impact

**Without budget (truncation):**
- Corrupted data → Need retry with different prompt
- 2-3 API calls per large filing
- Cost: $0.50-0.75 per large filing

**With budget (LLM-based smart selection):**
- Ranking call: gpt-4o-mini (~$0.001, cached if same task)
- Single extraction call with optimized sections
- First-time success (high-priority data intact)
- Cost: $0.201 per large filing

**Savings**: 
- vs. truncation: 60%+ by eliminating retries
- vs. naive ranking: LLM understands task context better than patterns
- Ranking cost amortized across many extractions with same task

## Production Considerations

### Token Counting Accuracy

- **With tiktoken** (recommended): Exact token counts matching OpenAI's tokenizer
- **Without tiktoken**: Conservative estimation (~4 chars/token, ~10% margin of error)

For production, install tiktoken:
```bash
pip install tiktoken
```

### Fallback Strategy

If token budget calculation is off by <10%:
- Budget manager reduces reserve further
- Request still succeeds (model respects context limit)
- Slight risk of truncation if estimate is very wrong

To be safer, reduce custom reserve:
```python
budget = ContextBudget("gpt-4o", reserve_tokens=3000)  # Larger reserve
```

### Monitoring

Check which sections were kept/dropped:

```
logger.info("Selected 4/12 sections (44,200 tokens): Income Statement, Balance Sheet, Cash Flow, MD&A")
```

Log budget decisions to track:
- How often sections are dropped
- Which sections are most valuable
- Whether reserve is adequate

## Future Enhancements

1. **Semantic ranking**: Use embeddings to score by relevance to specific query
2. **Composite sections**: Keep related tables together (Income Statement + footnotes)
3. **Hybrid strategy**: For budget-critical cases, use LLM-based summarization on dropped sections
4. **Statistics**: Track hit/miss ratio, average sections selected
5. **Custom scoring**: Allow users to override section priorities

## FAQ

**Q: Why not compress dropped sections?**
A: Compression (GZIP) reduces tokens by ~20-30%, but reading compressed data requires decompression context. Net savings minimal.

**Q: What if the extracted metric depends on a dropped section?**
A: Extraction accuracy suffers. To mitigate:
- Increase reserve tokens (keep more content)
- Pre-filter to high-priority sections only
- Use LLM-based query routing (determine required sections first)

**Q: How does this interact with caching?**
A: Cache key includes budgeted text, not raw text. Two identical filings may cache different results if budgeting differs. This is intentional (cache reflects actual API input).

**Q: Can I preview which sections will be dropped?**
A: Yes:
```python
sections = rank_sections(filing_text)
selected = select_sections_within_budget(sections, budget)
dropped = set(s.name for s in sections) - set(s.name for s in selected)
print(f"Will drop: {dropped}")
```
