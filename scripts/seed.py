import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.abspath("."))

from app.db.seed import seed_database
from app.db.session import AsyncSessionLocal, init_db
from app.logging import setup_logging

logging.basicConfig(level=logging.INFO)


async def main():
    setup_logging()
    print("Initializing database tables...")
    await init_db()
    print("Seeding database...")
    async with AsyncSessionLocal() as session:
        await seed_database(session, merchant_count=100)
    print("Database successfully seeded!")


if __name__ == "__main__":
    asyncio.run(main())
