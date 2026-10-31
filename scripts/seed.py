"""Seed the database with SIMULATED data.

    python scripts/seed.py           # idempotent seed (merge)
    python scripts/seed.py --reset   # drop and recreate all tables first (needed after schema changes)
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath("."))

from app.db.models import Base  # noqa: E402
from app.db.seed import seed_database  # noqa: E402
from app.db.session import AsyncSessionLocal, engine, init_db  # noqa: E402
from app.logging import setup_logging  # noqa: E402


async def main(reset: bool, merchants: int) -> None:
    setup_logging()
    if reset:
        print("Dropping all tables (--reset)...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    async with AsyncSessionLocal() as session:
        await seed_database(session, merchant_count=merchants)
    print("Database seeded (SIMULATED DATA).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--merchants", type=int, default=100)
    args = parser.parse_args()
    asyncio.run(main(args.reset, args.merchants))
