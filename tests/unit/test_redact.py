"""Secrets must never reach the embedder. Pure-stdlib, always green."""

from ingestion.redact import redact, register_redactor


def test_redacts_email():
    assert "[EMAIL]" in redact("ping alice@example.com about it")
    assert "alice@example.com" not in redact("ping alice@example.com about it")


def test_redacts_api_keys():
    out = redact("key sk-ant-abcd1234efgh and token ghp_abcd1234efgh")
    assert "sk-ant-abcd1234efgh" not in out
    assert "ghp_abcd1234efgh" not in out
    assert out.count("[SECRET]") == 2


def test_redacts_private_key_block():
    pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIabc\n-----END RSA PRIVATE KEY-----"
    assert redact(pem) == "[PRIVATE_KEY]"


def test_redacts_aws_key_id_jwt_and_bearer():
    assert "[AWS_KEY_ID]" in redact("key AKIAIOSFODNN7EXAMPLE here")
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.abc-DEF_123"
    assert "[JWT]" in redact(f"token {jwt}")
    assert "Bearer [REDACTED]" in redact("Authorization: Bearer abc.def.ghijklmnop")


def test_register_redactor_runs_after_patterns():
    register_redactor(lambda t: t.replace("Alice", "[NAME]"))
    assert "[NAME]" in redact("Alice paged on-call")


def test_leaves_plain_text_untouched():
    assert redact("the checkout service times out under load") == (
        "the checkout service times out under load"
    )
