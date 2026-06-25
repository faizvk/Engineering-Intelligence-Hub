"""The authenticated identity. Kept free of jwt/fastapi imports so the mapping is
unit-testable and importable by layers that shouldn't depend on the web stack.

`groups` drives document ACLs — a chunk is visible only if its acl[] overlaps the
principal's groups.
"""

from __future__ import annotations

from pydantic import BaseModel


class Principal(BaseModel):
    user_id: str
    groups: list[str]  # e.g. ["eng", "payments", "oncall"]


# When auth is disabled (demo), every request is this anonymous principal.
def default_principal() -> Principal:
    return Principal(user_id="anonymous", groups=["all"])


def principal_from_claims(claims: dict) -> Principal:
    return Principal(user_id=claims["sub"], groups=claims.get("groups", []))
