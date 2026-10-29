import pytest
import asyncio
import time
from src.ai_client import AsyncRateLimiter

@pytest.mark.asyncio
async def test_rate_limiter_allows_under_limit():
    limiter = AsyncRateLimiter(max_requests=5, time_window=1.0)
    start = time.monotonic()
    for _ in range(5):
        await limiter.acquire()
    elapsed = time.monotonic() - start
    assert elapsed < 0.2  # Immediate execution when under limit

@pytest.mark.asyncio
async def test_rate_limiter_throttles_over_limit():
    # 2 requests allowed per 0.4s window
    limiter = AsyncRateLimiter(max_requests=2, max_tokens=10000, time_window=0.4)
    start = time.monotonic()
    
    await limiter.acquire(estimated_tokens=100)
    await limiter.acquire(estimated_tokens=100)
    # Third request must wait until the first request expires from the window
    await limiter.acquire(estimated_tokens=100)
    
    elapsed = time.monotonic() - start
    assert elapsed >= 0.35  # Properly throttled

@pytest.mark.asyncio
async def test_rate_limiter_tpm_throttles():
    # Token limit of 500 per 0.4s window
    limiter = AsyncRateLimiter(max_requests=10, max_tokens=500, time_window=0.4)
    start = time.monotonic()

    # 1st request uses 300 tokens (allowed)
    await limiter.acquire(estimated_tokens=300)
    # 2nd request needs 300 tokens (300+300 > 500, must throttle)
    await limiter.acquire(estimated_tokens=300)

    elapsed = time.monotonic() - start
    assert elapsed >= 0.35  # Properly throttled by token budget
