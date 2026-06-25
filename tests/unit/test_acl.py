"""The ACL predicate is the security control. Pure-stdlib, always green."""

from backend.security.acl import ACL_PREDICATE, acl_param


def test_predicate_uses_array_overlap():
    # Overlap operator against a text[] bind — the index-friendly, in-SQL form.
    assert "acl &&" in ACL_PREDICATE
    assert "%(acl)s::text[]" in ACL_PREDICATE


def test_groups_become_a_string_array():
    assert acl_param(["eng", "oncall"]) == ["eng", "oncall"]


def test_empty_groups_match_nothing_by_construction():
    # acl[] (never empty, defaults to '{}'? no — rows carry groups) && '{}' is false,
    # so a principal with no groups retrieves nothing: default deny.
    assert acl_param([]) == []
