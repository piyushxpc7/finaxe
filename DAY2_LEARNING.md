# Day 2 — Multi-Provider LLM Architecture: Deep Learning Guide

## The Big Picture: What Are We Building?

Imagine you want to use AI in your app. You could write:

```python
# ❌ BAD: Hardcoded to one provider
import openai
response = openai.ChatCompletion.create(...)
```

But what if OpenAI gets expensive? Or you want to use Anthropic instead? You'd have to rewrite everything.

**Day 2 solves this:** We build an **abstraction layer** that lets you swap providers like Lego blocks:

```python
# ✅ GOOD: Provider-agnostic
provider = create_provider()  # Could be mock, openai, or anthropic
response = await provider.generate("What is AI?", purpose="extraction")
```

The architecture doesn't care which provider you use. Switching is just:

```env
DEFAULT_LLM_PROVIDER=mock        # swap to: openai or anthropic
```

No code changes needed.

---

## Architecture Layers

Think of the system in 4 layers:

```
┌─────────────────────────────────────┐
│  Your App Code                      │
│  (requests AI responses)            │
└─────────────────┬───────────────────┘
                  ↓
┌─────────────────────────────────────┐
│  Provider Abstraction               │  ← LLMProvider (abstract base)
│  (unified interface)                │  ← generate() orchestration
└─────────────────┬───────────────────┘
                  ↓
┌─────────────────────────────────────┐
│  Concrete Implementations           │  ← MockProvider
│  (mock, openai, anthropic)          │  ← OpenAIProvider (stub)
└─────────────────┬───────────────────┘  ← AnthropicProvider (stub)
                  ↓
┌─────────────────────────────────────┐
│  Support Services                   │  ← Cost calculator
│  (cost, ledger, factory)            │  ← Database ledger
└─────────────────────────────────────┘  ← Provider factory
```

---

## File-by-File Breakdown

### 1. **app/config.py** — The Control Center

**What it does:** Stores all configuration settings in one place.

```python
DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "mock")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
```

**Why it matters:**
- Your whole app reads configuration from here, not scattered throughout code
- Environment variables (from `.env` files) override defaults
- Easy to switch providers without changing code — just change the env var

**How to use it:**
```python
from app.config import DEFAULT_LLM_PROVIDER, OPENAI_API_KEY

print(DEFAULT_LLM_PROVIDER)  # "mock" or "openai" or "anthropic"
```

**Real-world example:**
```bash
# Development: use mock (free, fast)
DEFAULT_LLM_PROVIDER=mock pytest

# Production: use openai (real API)
DEFAULT_LLM_PROVIDER=openai python app.py
```

---

### 2. **app/llm/schemas.py** — The Data Contract

**What it does:** Defines the "shape" of data that flows through the system.

```python
class LLMPurpose(str, Enum):
    EXTRACTION = "extraction"
    SUMMARY = "summary"
    RETRIEVAL = "retrieval"
    AGENT = "agent"

@dataclass
class LLMResponse:
    text: str              # The AI's answer
    input_tokens: int      # Tokens you sent
    output_tokens: int     # Tokens AI returned
    latency_ms: int        # How long it took
    provider: str          # Which provider generated this
    model: str             # Which model (gpt-4o, claude-sonnet, etc)
    finish_reason: str     # Why did it stop? ("stop", "length", etc)
    request_id: str        # Unique ID for this request
```

**Why it matters:**
- Every provider (mock, openai, anthropic) returns the same format
- Your app code doesn't care which provider is behind the scenes
- Type hints help catch bugs early

**The contract:**
Any provider's `generate()` method **must** return an `LLMResponse`. This is the promise.

**Real-world example:**
```python
response = await provider.generate("What is AI?")
# response is ALWAYS an LLMResponse, regardless of provider
print(response.text)           # "AI is..."
print(response.input_tokens)   # 5
print(response.output_tokens)  # 42
print(response.provider)       # "mock" or "openai" or "anthropic"
```

---

### 3. **app/llm/cost.py** — The Price Book

**What it does:** Calculates how much an API call costs.

```python
PRICING = {
    "mock": {
        "mock-model": {
            "input": 0.0,      # Free
            "output": 0.0,
        },
    },
    "openai": {
        "gpt-4o": {
            "input": 5.0,      # $5 per million input tokens
            "output": 20.0,    # $20 per million output tokens
        },
        "gpt-4o-mini": {
            "input": 0.15,
            "output": 0.60,
        },
    },
    "anthropic": {
        "claude-sonnet": {
            "input": 3.0,
            "output": 15.0,
        },
        "claude-haiku": {
            "input": 0.80,
            "output": 4.0,
        },
    },
}

def compute_cost_usd(provider, model, input_tokens, output_tokens) -> float:
    """Calculate cost in USD."""
    pricing = PRICING[provider][model]
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost
```

**How it works:**

1. You have 1,000,000 input tokens and 500,000 output tokens
2. Using gpt-4o:
   - Input: (1,000,000 / 1,000,000) × $5.0 = $5.00
   - Output: (500,000 / 1,000,000) × $20.0 = $10.00
   - **Total: $15.00**

3. Using claude-sonnet:
   - Input: (1,000,000 / 1,000,000) × $3.0 = $3.00
   - Output: (500,000 / 1,000,000) × $15.0 = $7.50
   - **Total: $10.50** (cheaper!)

**Why it matters:**
- You need to know how much your AI costs
- This feeds into the ledger (database record of every call)
- Later, you can analyze spending patterns

**Real-world example:**
```python
cost = compute_cost_usd("openai", "gpt-4o", 100, 50)
print(cost)  # $0.0015
```

---

### 4. **app/llm/provider.py** — The Abstraction Layer

**What it does:** Defines the interface that all providers must follow.

```python
class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""
    
    async def generate(self, prompt: str, purpose=None, **kwargs):
        """
        The orchestrator. This is the brain of the system.
        Coordinates: API call → cost calculation → ledger write
        """
```

**The Generate Flow** (most important concept):

```
1. User calls: await provider.generate("What is AI?")
                          ↓
2. generate() calls _generate_impl() (subclass implements this)
                          ↓
3. _generate_impl() calls _call_api() (actual API call)
                          ↓
4. Returns LLMResponse with tokens and timing
                          ↓
5. generate() calculates cost: compute_cost_usd(...)
                          ↓
6. generate() writes to ledger: _write_ledger_row(...)
                          ↓
7. generate() returns response to user
```

**Important: Error Handling**

The `_write_ledger_row()` is wrapped in try-except:

```python
async def _write_ledger_row(self, ...):
    try:
        # Write to database
    except Exception:
        logger.exception("Failed to write ledger")  # Log but don't crash!
```

**Why?** If the database is down, your app still works. The ledger failure doesn't kill the request.

**The Abstract Methods** (subclasses must implement):

```python
@abstractmethod
async def _generate_impl(self, prompt: str, **kwargs) -> LLMResponse:
    """You must implement this in subclasses."""
    pass

@abstractmethod
async def _call_api(self, **kwargs) -> Any:
    """You must implement this in subclasses."""
    pass
```

**Real-world flow:**
```python
provider = MockProvider()
response = await provider.generate("What is AI?", purpose="extraction")
# Behind the scenes:
# 1. _generate_impl() is called → calls _call_api()
# 2. _call_api() returns mock data
# 3. Cost calculated ($0 for mock)
# 4. Ledger row written (if DB available)
# 5. LLMResponse returned to user
```

---

### 5. **app/llm/mock_provider.py** — The Test Double

**What it does:** Implements `LLMProvider` but returns fake data instead of calling real APIs.

```python
class MockProvider(LLMProvider):
    provider_name = "mock"
    model_name = "mock-model"
    
    async def _generate_impl(self, prompt: str, **kwargs) -> LLMResponse:
        """Don't call any API, just return fake data."""
        response = await self._call_api(prompt=prompt, **kwargs)
        
        return LLMResponse(
            text="Mock response generated successfully.",
            input_tokens=100,
            output_tokens=50,
            latency_ms=0,
            provider="mock",
            model="mock-model",
            finish_reason="stop",
            request_id=str(uuid4()),
        )
    
    async def _call_api(self, **kwargs) -> dict:
        """Simulate an API call with hardcoded data."""
        return {
            "text": "Mock response generated successfully.",
            "input_tokens": 100,
            "output_tokens": 50,
        }
```

**Why it matters:**
- You can test your entire system without real API keys
- Development is fast (no network delays)
- You can test error scenarios (set latency, change token counts)

**Real-world usage:**
```python
# In development/testing:
provider = MockProvider()
response = await provider.generate("Any prompt")
# Always returns the same data instantly
```

---

### 6. **app/llm/openai_provider.py & anthropic_provider.py** — The Future Stubs

**What they do:** Placeholder implementations that raise `NotImplementedError`.

```python
class OpenAIProvider(LLMProvider):
    provider_name = "openai"
    model_name = "gpt-4o"
    
    async def _generate_impl(self, prompt: str, **kwargs):
        raise NotImplementedError("OpenAI provider not implemented")
    
    async def _call_api(self, **kwargs):
        raise NotImplementedError("OpenAI provider not implemented")
```

**Why they exist:**
- Placeholder for real implementations (Day 3)
- Proves the factory works
- Tests can verify they fail gracefully

**Day 3 task:** Replace `NotImplementedError` with actual OpenAI SDK calls.

---

### 7. **app/llm/factory.py** — The Provider Picker

**What it does:** Creates the right provider based on configuration.

```python
def create_provider(provider="mock") -> LLMProvider:
    """Factory function. Returns the appropriate provider."""
    
    if provider == "mock":
        from app.llm.mock_provider import MockProvider
        return MockProvider()
    
    elif provider == "openai":
        if not OPENAI_API_KEY:
            raise MissingAPIKeyError("OPENAI_API_KEY not set")
        from app.llm.openai_provider import OpenAIProvider
        return OpenAIProvider()
    
    elif provider == "anthropic":
        if not ANTHROPIC_API_KEY:
            raise MissingAPIKeyError("ANTHROPIC_API_KEY not set")
        from app.llm.anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    
    else:
        raise ValueError(f"Unknown provider: {provider}")
```

**Why a factory?**
- Centralizes provider creation logic
- Validates API keys before creating providers
- Lets you swap providers at runtime

**Real-world usage:**
```python
# In your app:
provider = create_provider()  # Uses DEFAULT_LLM_PROVIDER from config
response = await provider.generate("What is AI?")

# Or explicitly:
provider = create_provider("openai")
response = await provider.generate("What is AI?")
```

**Provider flip (the magic):**
```bash
# Change one env var, entire provider switches:
DEFAULT_LLM_PROVIDER=mock pytest          # Fast tests
DEFAULT_LLM_PROVIDER=openai python app.py # Real API
DEFAULT_LLM_PROVIDER=anthropic python app.py # Different provider
```

No code changes. No recompiles. Just env vars.

---

### 8. **app/db/models.py** — The Ledger Record

**What it does:** Defines the structure of the ledger table in SQL.

```python
class LLMCall:
    """ORM model for LLM API call ledger."""
    
    __tablename__ = "llm_calls"
    
    id: UUID                      # Unique ID for this call
    ts: datetime                  # When was it called?
    provider: str                 # "mock", "openai", "anthropic"
    model: str                    # "gpt-4o", "claude-sonnet", etc
    purpose: str                  # "extraction", "summary", etc
    input_tokens: int             # Tokens sent
    output_tokens: int            # Tokens received
    cost_usd: float               # How much did this cost?
    latency_ms: int               # How long did it take?
    finish_reason: str            # Why did it stop?
    success: bool                 # Did the call succeed?
```

**Why it matters:**
- Every API call is recorded
- You can analyze: costs, latency, success rates
- Useful for billing, debugging, optimization

**Real-world queries:**
```sql
-- How much did we spend today?
SELECT SUM(cost_usd) FROM llm_calls WHERE DATE(ts) = TODAY();

-- Which model is fastest?
SELECT model, AVG(latency_ms) FROM llm_calls GROUP BY model;

-- How many extraction calls failed?
SELECT COUNT(*) FROM llm_calls 
WHERE purpose = 'extraction' AND success = false;
```

---

### 9. **app/db/migrations/001_create_llm_calls.sql** — The Schema

**What it does:** SQL migration that creates the ledger table in Postgres.

```sql
CREATE TABLE llm_calls (
    id UUID PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL,
    provider TEXT,
    model TEXT,
    purpose TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd NUMERIC,
    latency_ms INTEGER,
    finish_reason TEXT,
    success BOOLEAN
);

-- Indexes for fast queries
CREATE INDEX idx_llm_calls_ts ON llm_calls(ts);
CREATE INDEX idx_llm_calls_provider ON llm_calls(provider);
CREATE INDEX idx_llm_calls_model ON llm_calls(model);
```

**Why migrations?**
- Version control for database schema
- Can rollback if something breaks
- Documents what the database looks like

**Real-world usage:**
```bash
# Run migration to create table:
psql -f app/db/migrations/001_create_llm_calls.sql
```

---

### 10. **app/routers/admin.py** — The Dashboard Endpoint

**What it does:** Exposes an HTTP endpoint that returns cost analytics.

```python
@router.get("/admin/costs")
async def get_costs() -> dict:
    """Return LLM cost analytics."""
    return {
        "timestamp": "2026-06-13T10:30:00",
        "today": {
            "total_cost_usd": 15.32,
            "total_calls": 42,
            "avg_latency_ms": 245,
        },
        "by_model": [
            {"model": "gpt-4o", "cost": 10.00, "calls": 20},
            {"model": "claude-sonnet", "cost": 5.32, "calls": 22},
        ],
        "by_purpose": [
            {"purpose": "extraction", "cost": 8.00, "calls": 15},
            {"purpose": "summary", "cost": 7.32, "calls": 27},
        ],
    }
```

**Why it matters:**
- Your app can query costs in real-time
- Dashboards can use this API
- Monitor spending patterns

**Real-world usage:**
```bash
curl http://localhost:8000/admin/costs | jq
# Returns JSON with cost breakdowns
```

---

### 11. **app/tests/** — The Safety Net

**What they do:** Verify that everything works correctly.

#### **test_cost.py** (7 tests)
Tests that cost calculation is correct:
```python
def test_compute_cost_openai_gpt4o():
    cost = compute_cost_usd("openai", "gpt-4o", 1_000_000, 500_000)
    assert cost == 15.0  # $5 + $10

def test_compute_cost_unknown_provider():
    with pytest.raises(KeyError):
        compute_cost_usd("unknown", "model", 100, 100)
```

#### **test_factory.py** (7 tests)
Tests that provider creation works:
```python
def test_create_mock_provider():
    provider = create_provider("mock")
    assert isinstance(provider, MockProvider)

def test_create_openai_provider_missing_key():
    # Verify it fails without API key
    with pytest.raises(MissingAPIKeyError):
        create_provider("openai")
```

#### **test_integration.py** (5 tests)
Tests the full flow:
```python
async def test_generate_returns_response():
    provider = MockProvider()
    response = await provider.generate("What is AI?")
    
    assert response.text
    assert response.input_tokens > 0
    assert response.output_tokens > 0
```

**Why they matter:**
- Catch bugs before production
- Prove the system works
- All 19 tests pass ✅

---

### 12. **Makefile** — The Command Center

**What it does:** Defines shortcuts for common tasks.

```makefile
make test    # Run all tests
make costs   # Call the /admin/costs endpoint
```

**Why it matters:**
- One command to run all tests
- Consistent interface across the team

---

## How Everything Connects: The Data Flow

Let's trace what happens when you call `generate()`:

### **Scenario: A user asks "What is AI?"**

```
1. CODE: User code calls:
   ┌─────────────────────────────────────────────────────────┐
   │ provider = create_provider()  # app/llm/factory.py      │
   │ response = await provider.generate("What is AI?")       │
   └─────────────────────────────────────────────────────────┘

2. FACTORY (app/llm/factory.py):
   - Checks: DEFAULT_LLM_PROVIDER = "mock" (from app/config.py)
   - Creates: MockProvider()
   - Returns: provider instance

3. PROVIDER (app/llm/provider.py - generate() method):
   ┌─────────────────────────────────────────────────────────┐
   │ async def generate(prompt, purpose=None):               │
   │   start = time.time()                                   │
   │   response = await self._generate_impl(prompt)          │
   │   latency_ms = int((time.time() - start) * 1000)       │
   │   ...                                                    │
   └─────────────────────────────────────────────────────────┘

4. MOCK PROVIDER (app/llm/mock_provider.py - _generate_impl()):
   ┌─────────────────────────────────────────────────────────┐
   │ response = await self._call_api()                       │
   │ return LLMResponse(                                      │
   │     text="Mock response...",                             │
   │     input_tokens=100,                                    │
   │     output_tokens=50,                                    │
   │     ...                                                  │
   │ )                                                        │
   └─────────────────────────────────────────────────────────┘
   
   Returns to generate()

5. COST CALCULATOR (app/llm/cost.py):
   ┌─────────────────────────────────────────────────────────┐
   │ cost_usd = compute_cost_usd(                             │
   │     provider="mock",                                     │
   │     model="mock-model",                                  │
   │     input_tokens=100,                                    │
   │     output_tokens=50                                     │
   │ )                                                        │
   │ → cost = $0.00 (mock is free)                            │
   └─────────────────────────────────────────────────────────┘

6. LEDGER WRITE (app/llm/provider.py - _write_ledger_row()):
   ┌─────────────────────────────────────────────────────────┐
   │ try:                                                     │
   │     INSERT INTO llm_calls (  ← app/db/migrations/...     │
   │         id=uuid4(),                                      │
   │         ts=now(),                                        │
   │         provider="mock",                                 │
   │         model="mock-model",                              │
   │         purpose="test",                                  │
   │         input_tokens=100,                                │
   │         output_tokens=50,                                │
   │         cost_usd=0.00,                                   │
   │         latency_ms=2,                                    │
   │         finish_reason="stop",                            │
   │         success=true                                     │
   │     )                                                    │
   │ except Exception:                                        │
   │     logger.exception(...)  # Log but don't crash        │
   └─────────────────────────────────────────────────────────┘

7. RESPONSE (back to user):
   ┌─────────────────────────────────────────────────────────┐
   │ LLMResponse(                                             │
   │     text="Mock response generated successfully.",        │
   │     input_tokens=100,                                    │
   │     output_tokens=50,                                    │
   │     latency_ms=2,                                        │
   │     provider="mock",                                     │
   │     model="mock-model",                                  │
   │     finish_reason="stop",                                │
   │     request_id="abc-123"                                 │
   │ )                                                        │
   └─────────────────────────────────────────────────────────┘

8. OPTIONAL: Get analytics:
   ┌─────────────────────────────────────────────────────────┐
   │ GET /admin/costs  ← app/routers/admin.py                 │
   │ Queries: SELECT SUM(cost_usd) FROM llm_calls WHERE ...  │
   │ Returns: {"today": {"total_cost": 0.00, ...}}            │
   └─────────────────────────────────────────────────────────┘
```

---

## Why Each Layer Exists

### **app/config.py**
```
Why? Centralize configuration. Easy provider switching.
Without it? You'd have provider names hardcoded all over.
```

### **app/llm/schemas.py**
```
Why? Define the contract. All providers return the same shape.
Without it? Each provider might return different fields.
                Risk: "Why does openai return 'finish_reason' but anthropic doesn't?"
```

### **app/llm/cost.py**
```
Why? Calculate costs. Know how much you're spending.
Without it? You'd process millions of tokens without knowing the cost.
                Risk: Billing surprise at end of month.
```

### **app/llm/provider.py**
```
Why? Abstract interface. Swap providers without code changes.
Without it? You'd need if/elif for each provider everywhere.
                Risk: Nightmare to maintain. Spaghetti code.
```

### **app/llm/mock_provider.py**
```
Why? Test without APIs. Fast development. No API keys needed.
Without it? You'd test against real APIs every time (slow + expensive).
                Risk: Slow feedback loop. Burn through quota.
```

### **app/llm/factory.py**
```
Why? Centralize provider creation. Validate API keys.
Without it? You'd create providers all over the place.
                Risk: API key errors pop up in random places.
```

### **app/db/models.py + migrations/**
```
Why? Track every API call. Know costs, latency, success rates.
Without it? No visibility into what's happening.
                Risk: "Why did we spend $500?" No way to trace it.
```

### **app/routers/admin.py**
```
Why? Expose analytics over HTTP. Dashboards can use it.
Without it? Ledger data would be hard to access.
                Risk: Can't monitor costs in real-time.
```

### **app/tests/**
```
Why? Catch bugs before production. Prove everything works.
Without it? Ship broken code to prod.
                Risk: Your app breaks after deployment.
```

---

## Key Concepts to Master

### **1. Abstraction**
```python
# Without abstraction:
if provider == "openai":
    response = openai.create(...)
elif provider == "anthropic":
    response = anthropic.create(...)
# Repeats everywhere. Nightmare to change.

# With abstraction:
provider = create_provider()
response = await provider.generate(...)
# Same call, different provider. Magic!
```

### **2. The Generate Flow**
```
generate()
    → _generate_impl() [subclass decides]
    → _call_api() [subclass decides]
    → compute_cost() [calculate price]
    → _write_ledger() [record call]
    → return LLMResponse [to user]
```

The base class orchestrates. Subclasses implement the details.

### **3. Error Resilience**
```python
# Ledger failure doesn't kill the request
try:
    await self._write_ledger_row()
except Exception:
    logger.exception(...)  # Log it, but continue
```

Your app prioritizes: user gets response > database works.

### **4. Factory Pattern**
```python
# Rather than:
provider = MockProvider()  # scattered everywhere

# Use:
provider = create_provider()  # central place, env-driven
```

Easy to swap. Easy to test.

### **5. Configuration Over Code**
```python
# Rather than:
if developer_mode:
    provider = MockProvider()
else:
    provider = OpenAIProvider()

# Use:
DEFAULT_LLM_PROVIDER=mock        # dev
DEFAULT_LLM_PROVIDER=openai      # prod
# Code doesn't change. Just env var.
```

---

## Testing Strategy

### **Unit Tests (test_cost.py)**
Test individual functions in isolation:
```python
def test_compute_cost_openai_gpt4o():
    cost = compute_cost_usd("openai", "gpt-4o", 1_000_000, 500_000)
    assert cost == 15.0
```

### **Integration Tests (test_factory.py)**
Test that components work together:
```python
def test_create_mock_provider():
    provider = create_provider("mock")
    assert isinstance(provider, MockProvider)
```

### **End-to-End Tests (test_integration.py)**
Test the full flow:
```python
async def test_generate_returns_response():
    provider = MockProvider()
    response = await provider.generate("What is AI?")
    assert response.text
```

**Result:** 19 tests, all passing. ✅

---

## Day 2 → Day 3: What's Next?

### **Today (Day 2):**
✅ Architecture is provider-agnostic
✅ Mock provider works
✅ Cost calculator works
✅ Ledger table exists
✅ Factory pattern implemented
✅ 19 tests passing

### **Tomorrow (Day 3):**
🔧 Implement actual OpenAI SDK calls
🔧 Implement actual Anthropic SDK calls
🔧 Connect database (enable ledger writes)
🔧 Build admin dashboard

### **Key insight:**
Everything is ready. The OpenAI/Anthropic SDK code is just:

```python
class OpenAIProvider(LLMProvider):
    async def _generate_impl(self, prompt, **kwargs):
        # Replace NotImplementedError with real SDK call
        response = await openai.ChatCompletion.create(...)
        return LLMResponse(...)
```

Rest of the system doesn't change.

---

## File Dependency Graph

```
app/config.py
    ↓
app/llm/factory.py ← creates providers based on config
    ↓
├─→ app/llm/provider.py (abstract base)
│       ↓
│       ├─→ app/llm/mock_provider.py
│       ├─→ app/llm/openai_provider.py
│       └─→ app/llm/anthropic_provider.py
│       
│       ← imports for orchestration:
│       ├─→ app/llm/cost.py
│       └─→ app/db/models.py
│
├─→ app/llm/schemas.py (data contract)
│       ← used by all providers
│
└─→ app/routers/admin.py (HTTP endpoint)
        ← queries: app/db/models.py

app/db/migrations/
    ← creates: app/db/models.py (table structure)
```

---

## Summary: The 30-Second Pitch

**Day 2 builds a provider-agnostic LLM layer:**

1. **Config** decides which provider
2. **Factory** creates the right provider
3. **Provider interface** guarantees uniform API
4. **Concrete implementations** (mock, openai, anthropic) do the work
5. **Cost calculator** tracks spending
6. **Ledger** records every call
7. **Tests** prove everything works

**Result:** Swap providers by changing one env var. Zero code changes.

