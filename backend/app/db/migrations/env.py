import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import app.agents.models  # noqa: F401
import app.automation.models  # noqa: F401
import app.autonomy.models  # noqa: F401
import app.causal.models  # noqa: F401
import app.cognition.models  # noqa: F401
import app.communication.models  # noqa: F401
import app.context.models  # noqa: F401
import app.decision.models  # noqa: F401
import app.environment.models  # noqa: F401
import app.executive_memory.models  # noqa: F401

# Import all models to register them on Base.metadata for migrations
import app.identity.models  # noqa: F401
import app.intent.models  # noqa: F401  # noqa: F401
import app.knowledge.models  # noqa: F401
import app.knowledge_graph.models  # noqa: F401
import app.learning.models  # noqa: F401
import app.memory.models  # noqa: F401
import app.metacognition.models  # noqa: F401
import app.notifications.models  # noqa: F401
import app.observability.models  # noqa: F401
import app.perception.models  # noqa: F401
import app.planning.models  # noqa: F401
import app.orchestration.models  # noqa: F401
import app.situational_awareness.models  # noqa: F401
import app.policy.models  # noqa: F401
import app.prediction.models  # noqa: F401
import app.proactive.models  # noqa: F401
import app.resilience.models  # noqa: F401
import app.security.models  # noqa: F401
import app.simulation.models  # noqa: F401
import app.state.models  # noqa: F401
import app.verification.models  # noqa: F401
from app.core.config import get_settings
from app.db.session import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    settings = get_settings()
    url = settings.DATABASE_URL or "postgresql+asyncpg://kairo:kairo_secret@localhost:5432/kairo"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
