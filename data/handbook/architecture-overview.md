# Platform Architecture Overview

The platform is a set of services behind an API gateway. The gateway terminates
TLS, authenticates every request, applies rate limiting, and routes to the
backing services over the internal network.

## Core services

- **Auth service** — issues and refreshes JSON Web Tokens (JWTs). Owns the
  signing keys and the refresh-token rotation policy.
- **Checkout service** — orchestrates payment capture. Talks to the ledger and
  the payments provider. Maintains a Postgres connection pool.
- **Order service** — the system of record for orders. Receives signed internal
  requests forwarded by the gateway.
- **Ledger** — append-only record of money movement.

## Request path

1. The web client obtains a short-lived JWT from the auth service.
2. The gateway validates the JWT, enforces the per-user rate limit, and forwards
   a signed internal request (mTLS) to the target service.
3. The target service does its work and returns a response, which the gateway
   relays to the client.

## Data stores

Postgres is the primary datastore. The events pipeline moved off Kafka to a
Postgres-backed outbox in 2025 because the operational cost of a separate broker
outweighed its benefit at our throughput — see the migration ADR for the full
rationale.
