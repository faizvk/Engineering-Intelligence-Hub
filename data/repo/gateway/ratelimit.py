"""Per-user rate limiting at the gateway (Redis token bucket)."""

DEFAULT_RATE = 20      # requests/second per authenticated user
DEFAULT_BURST = 40
UNAUTH_RATE = 5        # requests/second per IP for login/health


class RateLimiter:
    """Token-bucket limiter. Only the gateway middleware calls this."""

    def __init__(self, redis, rate: int = DEFAULT_RATE, burst: int = DEFAULT_BURST):
        self._redis = redis
        self._rate = rate
        self._burst = burst

    def check(self, user_id: str) -> int:
        """Return remaining allowance; 0 means rate-limited (gateway returns 429)."""
        key = f"rl:{user_id}"
        remaining = self._redis.decr(key)
        if remaining < 0:
            return 0
        return remaining

    def reset(self, user_id: str) -> None:
        self._redis.set(f"rl:{user_id}", self._burst, ex=1)
