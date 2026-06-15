# Tranche 🔪

**Financial Data Extraction with Intelligent Caching & Context Optimization**

Extract structured financial metrics from SEC filings using LLMs, with intelligent context budgeting and Redis caching to minimize API costs.

> **Why "Tranche"?** In finance, a *tranche* is a slice of a larger deal. That's exactly what this engine does — it slices dense 100k-token filings into ranked sections, keeps the tranches that matter, and drops the rest to fit your context budget.

---

## 🎯 What It Does

1. **Extract Financial Metrics** - Parse 10-K/10-Q filings and extract structured data (revenue, net income, assets, etc.) using Claude/GPT
2. **Redis Caching** - Exact-match caching with SHA256 keys to eliminate duplicate API calls (50-95% cost savings)
3. **Context Budgeting** - Intelligently rank and select filing sections to fit within LLM token limits, never losing data integrity
4. **LLM-Based Ranking** - Use Claude to evaluate section relevance to your extraction task

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Redis (local or managed service)
- OpenAI/Claude API keys

### Installation

```bash
# Clone repo
git clone https://github.com/piyushxpc7/tranche.git
cd tranche

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your API keys and Redis URL
```

### Run Tests

```bash
# Test Redis caching layer
make cache

# Test context budget management  
make budget

# Run all tests
make test
```

---

## 🏗️ Architecture

### Three Core Layers

#### 1. **Redis Caching** (`app/llm/cache.py`)
```python
from app.llm.cache import get_cached_response, set_cached_response

# Check cache before API call
cached = await get_cached_response(model, prompt_version, user_message)

# Store result after API call
await set_cached_response(model, prompt_version, user_message, response, ttl_seconds)
```

**Key Features:**
- SHA256 cache keys: `SHA256(model:prompt_version:user_message)`
- Automatic TTL-based expiration (24 hours default)
- Graceful fallback if Redis unavailable
- Cost savings: $0.20 → $0.00 per duplicate request

#### 2. **Context Budget Management** (`app/llm/budget.py`)
```python
from app.llm.budget import ContextBudget

budget = ContextBudget("gpt-4o")  # 128k token limit
budgeted_text = await budget.budget_section_text(
    large_filing,
    system_prompt,
    user_template,
    task="Extract income statement metrics"
)
```

**How It Works:**
- Calculates available tokens after system/user prompts
- Ranks filing sections by relevance (using LLM)
- Selects top-scoring sections that fit within budget
- **Never splits sections** - keeps financial tables whole
- Cost savings: Eliminates retry costs from token overflow

#### 3. **LLM-Based Section Ranking** (`app/llm/ranker.py`)
```python
from app.llm.ranker import rank_sections

sections = await rank_sections(
    filing_text,
    task="Extract income statement metrics"
)
# Returns: [Section(name, content, score, tokens), ...]
# Ranked by LLM evaluation of relevance to task
```

**Advantages:**
- Task-aware scoring (not hardcoded patterns)
- Handles any section heading format
- Works with international filings
- Fallback heuristics if LLM unavailable

---

## 📈 Cost Impact

### Caching Alone
```
Without cache:  $0.20 × N identical requests
With cache:     $0.20 × 1 + $0.00 × (N-1)
Savings:        50-95% for duplicate-heavy workloads
```

### Context Budgeting Alone
```
Without budget: Large filing → overflow → retry → 2× cost
With budget:    Single call with optimized content
Savings:        50% by eliminating retries
```

### Combined
```
Large filing (first time):   1 API call ($0.20) → cached
Same filing (second time):   Redis hit (~10ms, $0.00)
Different filing:            1 API call ($0.20) → cached
Overall:                     60-95% cost savings
```

---

## 📁 Project Structure

```
tranche/
├── app/
│   ├── llm/
│   │   ├── cache.py          # Redis caching layer
│   │   ├── budget.py         # Context budget manager
│   │   ├── ranker.py         # LLM-based section ranking
│   │   ├── tokenizer.py      # Token counting (tiktoken + fallback)
│   │   ├── chains/           # Extraction chains
│   │   ├── extraction/       # Financial data extraction
│   │   ├── schemas/          # Pydantic models
│   │   ├── config.py         # Configuration
│   │   └── (other modules)
│   ├── db/                   # Database models & migrations
│   ├── routers/              # API endpoints
│   └── tests/
├── scripts/
│   ├── test_cache.py         # Cache behavior tests
│   ├── test_budget.py        # Budget management tests
│   ├── test_day4.py          # Extraction chain tests
│   └── test_extraction.py
├── buyside/                  # FastAPI template
├── prompts/                  # LLM prompt templates
├── migrations/               # Database migrations
│
├── requirements.txt          # Python dependencies
├── Makefile                  # Common tasks
├── .env.example              # Environment template
├── CACHING.md                # Caching deep dive
├── CONTEXT_BUDGET.md         # Budget management guide
└── README.md                 # This file
```

---

## 🔧 Configuration

### Environment Variables (`.env`)

```bash
# LLM API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Redis Cache
REDIS_URL=redis://localhost:6379
CACHE_TTL_SECONDS=86400  # 24 hours

# Database (optional)
DATABASE_URL=postgresql://user:password@localhost/tranche
```

### Redis Setup

**Local (Homebrew):**
```bash
brew install redis
redis-server
```

**Docker:**
```bash
docker run -d -p 6379:6379 redis:latest
```

**Production:**
```bash
# AWS ElastiCache, Azure Redis, or Redis Cloud
REDIS_URL=redis://prod-endpoint:6379
```

---

## 📊 Key Features

### ✅ Exact-Match Caching
- SHA256 keys include model, prompt version, and input
- Automatic invalidation when prompts change
- Safe for production (TTL enforced)
- No fuzzy/semantic matching (deterministic)

### ✅ Intelligent Context Budgeting
- Respects model token limits (gpt-4o: 128k, gpt-4: 8k, etc.)
- Never truncates mid-table (preserves data integrity)
- Ranks sections by task relevance
- Graceful overflow handling

### ✅ Task-Aware Section Ranking
- LLM evaluates relevance to your extraction task
- Handles novel section headings
- Works with any filing format
- Fallback heuristics if LLM unavailable

### ✅ Cost Optimization
- Eliminates duplicate API calls
- Prevents retry costs from token overflow
- Configurable TTL and reserves
- Production-ready error handling

---

## 💻 Usage Examples

### Basic Extraction with Caching

```python
from app.chains.extraction import build_extraction_chain

# Build chain (includes caching + budgeting)
chain = build_extraction_chain(model="gpt-4o")

# First request: API call + caching
result = await chain.ainvoke({
    "ticker": "AAPL",
    "fiscal_year": 2023,
    "period_type": "annual",
    "section_text": filing_text,  # May be 100k+ tokens
})

# Second request with same input: Cache hit (~10ms)
result = await chain.ainvoke({...})  # Same inputs
# → Returns cached result instantly, no API call
```

### Direct Cache Usage

```python
from app.llm.cache import get_cached_response, set_cached_response

# Check cache
cached = await get_cached_response("gpt-4o", "v1", "Extract AAPL metrics")

if not cached:
    # API call
    response = await api.call(...)
    
    # Cache result
    await set_cached_response("gpt-4o", "v1", "Extract AAPL metrics", response)
```

### Context Budgeting with Large Filings

```python
from app.llm.budget import ContextBudget

budget = ContextBudget("gpt-4o")

# Large filing (100k tokens) → optimized (45k tokens)
budgeted_text = await budget.budget_section_text(
    filing_text,
    system_prompt,
    user_template,
    task="Extract revenue, expenses, net income"
)

# Result: Income Statement + Balance Sheet (kept whole)
# Dropped: Risk Factors, Management Discussion (low priority)
```

---

## 🧪 Testing

All features are thoroughly tested:

```bash
# Redis caching tests
make cache
# ✓ Cache key generation (SHA256 with model + version + input)
# ✓ Cache miss → hit behavior
# ✓ Prompt version invalidation

# Context budget tests
make budget
# ✓ Section ranking (by LLM relevance)
# ✓ Budget selection keeps sections whole
# ✓ Large filings trimmed intelligently

# All tests
make test
```

---

## 📚 Documentation

- **[CACHING.md](CACHING.md)** - Deep dive into Redis caching architecture
- **[CONTEXT_BUDGET.md](CONTEXT_BUDGET.md)** - Context budget management guide
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Full implementation details

---

## 🛠️ Development

### Add New Features
```bash
pip install -r requirements.txt
python -m pytest app/tests/
```

### Code Quality
```bash
make lint      # Run linters (ruff, black)
make format    # Auto-format code
```

---

## 📝 License

MIT - See LICENSE file

---

## 👤 Author

**Piyush Chandra**  
Email: piyushcapitals@gmail.com  
GitHub: [@piyushxpc7](https://github.com/piyushxpc7)

---

## 🚀 Roadmap

- [ ] Add cache hit/miss metrics dashboard
- [ ] Implement batch cache invalidation
- [ ] LLM-based query routing (determine required sections)
- [ ] Support for other filing formats (XBRL, iXBRL)
- [ ] Distributed caching (Redis Cluster)
- [ ] Integration with financial data APIs

---

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing documentation in CACHING.md and CONTEXT_BUDGET.md

---

**Made with ❤️ for financial data extraction**
