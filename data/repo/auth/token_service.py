"""Auth service token issuance and refresh-token rotation (ADR-0007)."""

import secrets
import time

ACCESS_TOKEN_TTL = 15 * 60  # 15 minutes
REFRESH_TOKEN_TTL = 30 * 24 * 3600  # 30 days


class TokenService:
    """Issues short-lived access tokens and rotates refresh tokens on use."""

    def __init__(self, signer, store):
        self._signer = signer  # RS256 JWT signer
        self._store = store  # hashed refresh-token store (Postgres)

    def issue(self, user_id: str, groups: list[str]) -> dict:
        access = self._signer.sign(
            {"sub": user_id, "groups": groups, "exp": time.time() + ACCESS_TOKEN_TTL}
        )
        refresh = secrets.token_urlsafe(32)
        self._store.save(user_id, _hash(refresh), ttl=REFRESH_TOKEN_TTL)
        return {"access_token": access, "refresh_token": refresh}

    def refresh(self, user_id: str, refresh_token: str) -> dict:
        record = self._store.lookup(user_id, _hash(refresh_token))
        if record is None or record.revoked:
            # Reuse of a rotated/revoked token is treated as theft.
            self._store.revoke_family(user_id)
            raise PermissionError("refresh token reuse detected")
        # Rotate: invalidate the presented token and mint a fresh pair.
        self._store.revoke(record.id)
        return self.issue(user_id, record.groups)


def _hash(token: str) -> str:
    import hashlib

    return hashlib.sha256(token.encode()).hexdigest()
