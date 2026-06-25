"""Secrets must never reach the embedder. Pure-stdlib, always green."""

from ingestion.redact import redact


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


def test_leaves_plain_text_untouched():
    assert redact("the checkout service times out under load") == (
        "the checkout service times out under load"
    )
