# Auth Service: Tokens & Refresh

The auth service issues short-lived access tokens and longer-lived refresh
tokens, and owns the rotation strategy chosen in ADR-0007.

## Token issuance

On login, the service mints an **access token** (a signed JWT, RS256, 15-minute
expiry) and a **refresh token** (opaque, 30-day expiry, stored hashed in
Postgres). The access token carries the user id (`sub`) and group membership
(`groups`), which downstream services use for authorization.

## Refresh & rotation

When the access token expires, the client presents its refresh token to
`POST /auth/refresh`. The service:

1. Looks up the hashed refresh token; rejects if missing or revoked.
2. Issues a new access token.
3. **Rotates** the refresh token — the old one is invalidated and a new one
   returned. Reuse of a rotated refresh token is treated as theft and revokes
   the whole token family.

This rotation-on-refresh strategy limits the blast radius of a stolen refresh
token. The code lives in `auth/token_service.py`.

## Validation by the gateway

The gateway validates the access token's signature against the auth service's
public JWKS and forwards `sub`/`groups` to backing services over mTLS. Services
never re-validate the signature; they trust the gateway's internal request.
