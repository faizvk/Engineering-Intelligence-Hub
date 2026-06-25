"""Principal mapping — pure (no jwt/fastapi), so it runs green everywhere."""

from backend.security.principal import default_principal, principal_from_claims


def test_default_principal_is_anonymous_all():
    p = default_principal()
    assert p.user_id == "anonymous"
    assert p.groups == ["all"]


def test_principal_from_claims():
    p = principal_from_claims({"sub": "u-42", "groups": ["eng", "payments"]})
    assert p.user_id == "u-42"
    assert p.groups == ["eng", "payments"]


def test_principal_missing_groups_defaults_empty():
    p = principal_from_claims({"sub": "u-1"})
    assert p.groups == []
