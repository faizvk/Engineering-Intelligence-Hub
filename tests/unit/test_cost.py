"""The cost model matches the verified pricing and credits cache reads at 0.1x.
Pure-stdlib (duck-typed usage), always green.
"""

from types import SimpleNamespace

from backend.cost.meter import cache_hit, cost_usd


def _usage(model, it=0, ot=0, crit=0, ccit=0):
    return SimpleNamespace(
        model=model,
        input_tokens=it,
        output_tokens=ot,
        cache_read_input_tokens=crit,
        cache_creation_input_tokens=ccit,
    )


def test_sonnet_input_output_cost():
    # 1M input @ $3 + 1M output @ $15 = $18.
    assert cost_usd(_usage("claude-sonnet-4-6", it=1_000_000, ot=1_000_000)) == 18.0


def test_cache_read_is_one_tenth_input():
    # 1M cache-read tokens on Sonnet bill at $3 * 0.1 = $0.30.
    assert round(cost_usd(_usage("claude-sonnet-4-6", crit=1_000_000)), 4) == 0.30


def test_opus_is_pricier_than_sonnet():
    u = dict(it=10_000, ot=2_000)
    assert cost_usd(_usage("claude-opus-4-8", **u)) > cost_usd(_usage("claude-sonnet-4-6", **u))


def test_cache_hit_flag():
    assert cache_hit(_usage("claude-sonnet-4-6", crit=2048)) is True
    assert cache_hit(_usage("claude-sonnet-4-6")) is False
