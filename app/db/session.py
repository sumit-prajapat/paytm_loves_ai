from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.db.models import Base

settings = get_settings()

# Configure engine with connection arguments appropriate for SQLite or Postgres
connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args["check_same_thread"] = False

engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class SchemaOutOfDate(RuntimeError):
    pass


def _missing_columns(sync_conn) -> list[str]:
    from sqlalchemy import inspect

    insp = inspect(sync_conn)
    missing = []
    for table in Base.metadata.sorted_tables:
        if not insp.has_table(table.name):
            continue
        existing = {c["name"] for c in insp.get_columns(table.name)}
        missing += [f"{table.name}.{c.name}" for c in table.columns if c.name not in existing]
    return missing


async def init_db() -> None:
    """Create missing tables, then fail fast if existing tables predate the current schema
    (create_all never adds columns; Alembic migrations arrive in Step F)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        missing = await conn.run_sync(_missing_columns)
    if missing:
        raise SchemaOutOfDate(
            f"Database schema is out of date (missing {missing[:5]}...). "
            "Re-create the SIMULATED demo DB with: python scripts/seed.py --reset"
        )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for yielding an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
