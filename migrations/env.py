"""Alembic environment. Reads the DB URL from typed settings (no secret in ini).

Schema is managed with hand-written op.execute() DDL (the project uses raw SQL,
not the ORM), so target_metadata is None.
"""

from __future__ import annotations

from alembic import context
from sqlalchemy import create_engine

from core.settings import get_settings

target_metadata = None


def _url() -> str:
    return get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(url=_url(), literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url(), pool_pre_ping=True)
    with engine.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
