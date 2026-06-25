"""JWT bearer auth. Every protected route depends on current_principal.

A verified RS256 JWT (issued by your IdP) carries the user id and group
membership. When AUTH_ENABLED is false, the dependency returns the anonymous
principal so the demo runs without an IdP.
"""

from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.security.principal import Principal, default_principal, principal_from_claims
from core.settings import get_settings

bearer = HTTPBearer(auto_error=False)


def current_principal(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Principal:
    s = get_settings()
    if not s.auth_enabled:
        return default_principal()
    if cred is None or not s.jwt_public_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    try:
        claims = jwt.decode(
            cred.credentials,
            s.jwt_public_key.get_secret_value(),
            algorithms=["RS256"],
            audience=s.jwt_audience,
        )
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token")
    return principal_from_claims(claims)
