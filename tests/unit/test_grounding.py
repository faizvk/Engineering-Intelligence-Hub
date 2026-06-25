"""Citation spans must trace back to the retrieved context. Pure-stdlib, green."""

from evals.grounding import grounded_fraction, is_grounded

CONTEXTS = [
    "Run make rotate-db-creds ENV=staging to rotate credentials.",
    "The access token is a 15-minute RS256 JWT.",
]


def test_grounded_span_found():
    assert is_grounded("make rotate-db-creds ENV=staging", CONTEXTS) is True


def test_ungrounded_span_not_found():
    assert is_grounded("delete the production database", CONTEXTS) is False


def test_whitespace_and_case_insensitive():
    assert is_grounded("15-MINUTE   rs256  jwt", CONTEXTS) is True


def test_fraction():
    quoted = ["make rotate-db-creds ENV=staging", "hallucinated claim"]
    assert grounded_fraction(quoted, CONTEXTS) == 0.5


def test_no_claims_is_vacuously_grounded():
    assert grounded_fraction([None, ""], CONTEXTS) == 1.0
