# Rate Limiting at the Gateway

The gateway enforces a per-user rate limit using the `RateLimiter` class, backed
by a Redis token bucket.

## Configured limits

- **Default:** 20 requests/second per authenticated user, burst 40.
- **Unauthenticated** (login, health): 5 requests/second per IP.
- **Internal service-to-service** traffic is exempt — it is trusted after mTLS.

The limits are configured in `gateway/ratelimit.yaml` and reloaded without a
restart. `RateLimiter.check(user_id)` returns the remaining allowance; when it
hits zero the gateway returns `429 Too Many Requests` with a `Retry-After`
header.

## Who calls RateLimiter

Only the gateway middleware calls `RateLimiter`. Backing services never rate
limit directly; they assume the gateway already did. If you add a new public
route, it inherits the default limit automatically — opt out only for internal
endpoints.
