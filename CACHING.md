# Redis Caching Implementation

## Overview

The Days project now includes **exact-match Redis caching** for LLM API calls. This prevents duplicate API calls and reduces costs while maintaining cache safety through prompt versioning.

## Architecture

### Cache Key Strategy

Cache keys are generated using **SHA256 hashing** of three components:

```
key = SHA256(model + ":" + prompt_version + ":" + user_message)
```

**Why this approach?**

1. **Model included**: Different models (gpt-4o vs gpt-4-turbo) have different costs and outputs
2. **Prompt version included**: Changing prompts changes answers → different cache entry
   - Prompt v1 → one cache
   - Prompt v2 → different cache (auto-invalidation on breaking changes)
3. **User message included**: Exact-match only (no fuzzy matching)
   - Different ticker, year, or filing = different cache
   - Same input twice = instant hit

### Flow

#### First Request (Cache Miss)

```
Question: Extract AAPL FY2023 revenue
         ↓
Redis lookup (SHA256 key)
         ↓
Not found
         ↓
Call OpenAI API (3+ seconds)
         ↓
Store result in Redis with TTL
         ↓
Return result
```

**Cost**: Full API call (counted in ledger)

#### Second Request (Cache Hit)

```
Question: Extract AAPL FY2023 revenue (identical)
         ↓
Redis lookup
         ↓
Found in 10ms
         ↓
Return cached result
         ↓
NO API call
```

**Cost**: Zero (no API call, no ledger entry)

## Integration Points

### 1. Cache Module (`app/llm/cache.py`)

Core caching functions:

```python
# Check if cached
cached = await get_cached_response(model, prompt_version, user_message)

# Store result
await set_cached_response(model, prompt_version, user_message, response_dict, ttl_seconds)

# Invalidate on demand
await invalidate_cache(model, prompt_version, user_message)
```

### 2. Extraction Chain (`app/chains/extraction.py`)

The chain now:

1. **Before API call**: Check cache for exact match
2. **On cache hit**: Return cached metrics immediately (logs "Cache hit for TICKER PERIOD")
3. **On cache miss**: Call API as before
4. **After API call**: Store result in cache for future requests
5. **Cost ledger**: Only written on cache miss (actual API call)

### 3. Configuration (`app/config.py`)

Two new settings:

```python
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "86400"))
```

## Setup & Usage

### Install Redis

**Local (macOS with Homebrew)**:
```bash
brew install redis
brew services start redis
```

**Docker**:
```bash
docker run -d -p 6379:6379 redis:latest
```

### Python Dependencies

```bash
pip install -r requirements.txt
```

Includes: `redis==5.0.1` (async-only client)

### Environment Configuration

Copy `.env.example` and set:

```bash
REDIS_URL=redis://localhost:6379
CACHE_TTL_SECONDS=86400  # 24 hours
```

### Run Tests

```bash
python scripts/test_cache.py
```

Verifies:
- Cache key generation (same input → same key)
- Cache miss → hit behavior
- Prompt version invalidation (v1 ≠ v2)

## Cost Impact Example

**Without caching:**
- Extract AAPL FY2023: $0.20 (first call)
- Extract AAPL FY2023: $0.20 (second call - duplicate!)
- Extract AAPL FY2023: $0.20 (third call - duplicate!)
- **Total: $0.60 for 3 identical requests**

**With caching:**
- Extract AAPL FY2023: $0.20 (first call, cached)
- Extract AAPL FY2023: $0.00 (cache hit, ~10ms)
- Extract AAPL FY2023: $0.00 (cache hit, ~10ms)
- **Total: $0.20 for 3 identical requests (66% savings)**

## Graceful Degradation

If Redis is unavailable:

1. Cache reads return `None` (cache miss)
2. API call happens as normal
3. Cache write fails silently (logged as warning)
4. System continues working (no errors)

Set `REDIS_URL=disabled` to skip Redis entirely.

## Safety Guarantees

1. **No stale data**: TTL enforced (default 24h)
2. **No cross-model contamination**: Model in key
3. **No breaking changes**: Prompt version in key
   - Upgrade extraction-v1→v2? Cache invalidates automatically
   - Old v1 cache stays separate
4. **Exact match only**: No fuzzy/semantic matching
   - Different tickers = different cache
   - Different filing text = different cache

## Monitoring

Check cache metrics:

```bash
redis-cli
> KEYS *                    # See all cached entries
> DBSIZE                    # Total entries
> TTL <key>                 # Time to live on key
> FLUSHDB                   # Clear all (careful!)
```

Log cache hits:
```bash
PYTHONPATH=. python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
# Run extraction that hits cache
"
```

## Future Enhancements

1. **Cache statistics**: Track hit/miss ratio per model
2. **Batch invalidation**: Clear cache by pattern (e.g., "extraction-v1:*")
3. **Compression**: Store larger responses with gzip
4. **Distributed caching**: Redis Cluster for production
5. **Cache warming**: Pre-populate common queries
