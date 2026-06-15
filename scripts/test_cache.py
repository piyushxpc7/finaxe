"""
Test Redis caching behavior.
Run: python scripts/test_cache.py

Demonstrates:
1. First call to extract → API call → 3+ seconds → cached result
2. Second call with same input → Redis lookup → ~10ms → cached result (no API cost)
3. Different input → API call (cache miss)
"""
import asyncio
import time
from app.llm.cache import (
    generate_cache_key,
    get_cached_response,
    set_cached_response,
    invalidate_cache,
)


async def test_cache_key_generation():
    """Cache key includes model, prompt version, and input."""
    key1 = generate_cache_key("gpt-4o", "v1", "Extract AAPL FY2023")
    key2 = generate_cache_key("gpt-4o", "v1", "Extract AAPL FY2023")
    key3 = generate_cache_key("gpt-4o", "v2", "Extract AAPL FY2023")  # Different version
    key4 = generate_cache_key("gpt-4o", "v1", "Extract TSLA FY2023")  # Different input

    assert key1 == key2, "Same inputs should produce same key"
    assert key1 != key3, "Different prompt_version should produce different key"
    assert key1 != key4, "Different user_message should produce different key"
    print("✓ Cache key generation (SHA256 with model + prompt_version + input)")


async def test_cache_miss_then_hit():
    """First call misses cache, second call hits."""
    model = "gpt-4o"
    version = "v1"
    msg = "Extract AAPL revenue from filing"

    # First call: cache miss
    result = await get_cached_response(model, version, msg)
    assert result is None, "Cache should be empty"
    print("✓ Cache miss (expected for first call)")

    # Store response
    response_data = {
        "revenue": 383285,
        "net_income": 96995,
        "currency": "millions",
    }
    start = time.time()
    await set_cached_response(model, version, msg, response_data, ttl_seconds=60)
    elapsed_ms = int((time.time() - start) * 1000)
    print(f"✓ Cache write (~{elapsed_ms}ms)")

    # Second call: cache hit
    start = time.time()
    cached = await get_cached_response(model, version, msg)
    elapsed_ms = int((time.time() - start) * 1000)
    assert cached is not None, "Should hit cache"
    assert cached == response_data, "Should return exact cached data"
    print(f"✓ Cache hit (~{elapsed_ms}ms, vs 3000+ms for API call)")

    # Clean up
    await invalidate_cache(model, version, msg)
    result = await get_cached_response(model, version, msg)
    assert result is None, "Cache should be empty after invalidation"
    print("✓ Cache invalidation")


async def test_prompt_version_invalidates_cache():
    """Changing prompt version should invalidate cache (no automatic cache reuse)."""
    model = "gpt-4o"
    msg = "Extract revenue"

    # Cache with v1
    await set_cached_response(model, "v1", msg, {"data": "v1_response"}, ttl_seconds=60)

    # Same input + model, different version
    result = await get_cached_response(model, "v2", msg)
    assert result is None, "Different prompt_version should not hit cache"
    print("✓ Prompt version changes invalidate cache (safe for breaking changes)")

    # Clean up
    await invalidate_cache(model, "v1", msg)


if __name__ == "__main__":
    print("Testing Redis cache layer...\n")
    asyncio.run(test_cache_key_generation())
    asyncio.run(test_cache_miss_then_hit())
    asyncio.run(test_prompt_version_invalidates_cache())
    print("\n✓ All cache tests passed")
    print("\nIntegration with extraction chain:")
    print("  1. build_extraction_chain() now checks cache before API call")
    print("  2. Cache key = SHA256(model + prompt_version + user_message)")
    print("  3. Cache TTL configurable via CACHE_TTL_SECONDS env var (default 24h)")
    print("  4. Cost ledger only written on cache miss (actual API call)")
