"""Pure-Python guardrails on the verified platform facts. No third-party deps,
so this runs green in any environment and pins the pricing the cost model uses.
"""

from core.constants import (
    CACHE_READ_MULT,
    CACHE_WRITE_MULT,
    MIN_CACHE_PREFIX_TOKENS,
    PRICING,
)


def test_three_claude_tiers_priced():
    assert set(PRICING) == {
        "claude-opus-4-8",
        "claude-sonnet-4-6",
        "claude-haiku-4-5",
    }


def test_verified_prices():
    assert PRICING["claude-opus-4-8"] == {"in": 5.00, "out": 25.00}
    assert PRICING["claude-sonnet-4-6"] == {"in": 3.00, "out": 15.00}
    assert PRICING["claude-haiku-4-5"] == {"in": 1.00, "out": 5.00}


def test_cache_multipliers():
    assert CACHE_READ_MULT == 0.10  # reads ~0.1x input
    assert CACHE_WRITE_MULT == 1.25  # 5-min write


def test_min_cache_prefix():
    # Sonnet caches a shorter prefix than Opus/Haiku.
    assert MIN_CACHE_PREFIX_TOKENS["claude-sonnet-4-6"] == 2048
    assert MIN_CACHE_PREFIX_TOKENS["claude-opus-4-8"] == 4096
    assert MIN_CACHE_PREFIX_TOKENS["claude-haiku-4-5"] == 4096
