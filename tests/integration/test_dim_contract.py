"""Contract: EMBED_DIM must equal the vector(N) column width, or inserts fail.
pgvector stores the dimension as atttypmod - 4. Skips when DB/config is absent.
"""

import pytest

psycopg = pytest.importorskip("psycopg")


def test_embed_dim_matches_column():
    try:
        from core.settings import get_settings

        s = get_settings()
    except Exception:
        pytest.skip("settings not configured (API keys absent)")

    try:
        conn = psycopg.connect(s.database_url_raw)
    except Exception:
        pytest.skip("no database available")
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT atttypmod FROM pg_attribute "
                "WHERE attrelid = 'prose_chunks'::regclass AND attname = 'embedding'"
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if not row or row[0] is None:
        pytest.skip("prose_chunks not created")
    assert row[0] - 4 == s.embed_dim
