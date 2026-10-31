import datetime
import logging
import random

from faker import Faker
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.heroes import seed_heroes
from app.db.loaders.airports_loader import load_airports
from app.db.loaders.flights_loader import load_flights
from app.db.loaders.paysim_loader import load_paysim_transactions
from app.db.loaders.routes_loader import load_routes
from app.db.models import (
    Device,
    Festival,
    LoanProfile,
    Merchant,
    Policy,
    Settlement,
    SettlementItem,
    Transaction,
)
from app.rag.policies import SUPPORT_POLICIES

logger = logging.getLogger(__name__)

# Indian cities and corresponding state & language mappings
INDIAN_CITIES = [
    {"city": "Delhi", "state": "Delhi", "language": "hi"},
    {"city": "Mumbai", "state": "Maharashtra", "language": "mr"},
    {"city": "Pune", "state": "Maharashtra", "language": "mr"},
    {"city": "Jaipur", "state": "Rajasthan", "language": "hi"},
    {"city": "Lucknow", "state": "Uttar Pradesh", "language": "hi"},
    {"city": "Patna", "state": "Bihar", "language": "hi"},
    {"city": "Varanasi", "state": "Uttar Pradesh", "language": "hi"},
    {"city": "Kolkata", "state": "West Bengal", "language": "bn"},
    {"city": "Chennai", "state": "Tamil Nadu", "language": "ta"},
    {"city": "Coimbatore", "state": "Tamil Nadu", "language": "ta"},
    {"city": "Ahmedabad", "state": "Gujarat", "language": "gu"},
    {"city": "Surat", "state": "Gujarat", "language": "gu"},
    {"city": "Indore", "state": "Madhya Pradesh", "language": "hi"},
    {"city": "Bhopal", "state": "Madhya Pradesh", "language": "hi"},
    {"city": "Bangalore", "state": "Karnataka", "language": "en"},
    {"city": "Hyderabad", "state": "Telangana", "language": "en"},
    {"city": "Chandigarh", "state": "Punjab", "language": "hi"},
]

BUSINESS_TYPES = ["kirana", "tailor", "chemist", "tea_stall", "electronics", "sweet_shop", "apparel"]

UPCOMING_FESTIVALS = [
    {"date": "2026-11-08", "name": "Diwali (Deepavali)", "region": "National"},
    {"date": "2026-11-10", "name": "Bhai Dooj", "region": "North & West"},
    {"date": "2026-11-15", "name": "Chhath Puja", "region": "Bihar & UP"},
    {"date": "2026-12-25", "name": "Christmas", "region": "National"},
    {"date": "2027-01-14", "name": "Makar Sankranti / Pongal", "region": "National"},
    {"date": "2027-03-23", "name": "Holi", "region": "National"},
]


async def seed_database(db: AsyncSession, merchant_count: int = 150) -> None:
    """Seeds the database deterministically with ~200 merchants, devices, 90-day transactions,

    settlements with anomalies, hero data, flights, airports, festivals, and policies.
    """
    logger.info("Starting deterministic database seed...")
    # Fixed random seed for repeatability
    random.seed(42)
    fake = Faker("en_IN")
    Faker.seed(42)

    now = datetime.datetime.now(datetime.timezone.utc)
    today = datetime.date.today()

    # 1. Seed Policies
    for pol in SUPPORT_POLICIES:
        await db.merge(Policy(
            id=pol["id"],
            title=pol["title"],
            text=pol["text"],
            language=pol["language"],
        ))

    # 2. Seed Festivals (and clear rows that would otherwise duplicate on re-seed)
    await db.execute(delete(Festival))
    await db.execute(delete(SettlementItem).where(SettlementItem.settlement_id.like("set_m_%")))
    for fest in UPCOMING_FESTIVALS:
        await db.merge(Festival(
            date=fest["date"],
            name=fest["name"],
            region=fest["region"],
        ))

    # 3-4. Playbooks, hero personas, travel bookings and demo users (idempotent)
    await seed_heroes(db)

    # 5. Seed ~150 Realistic Indian Merchants across 17 cities
    logger.info(f"Generating {merchant_count} synthetic merchants and transactions...")
    for i in range(1, merchant_count + 1):
        m_id = f"m_{1000 + i}"
        city_meta = random.choice(INDIAN_CITIES)
        b_type = random.choice(BUSINESS_TYPES)
        merchant_name = f"{fake.first_name()} {b_type.replace('_', ' ').title()} Store"
        device_id = f"sb_{2000 + i}"

        merchant = Merchant(
            id=m_id,
            name=merchant_name,
            city=city_meta["city"],
            state=city_meta["state"],
            language=city_meta["language"],
            business_type=b_type,
            device_id=device_id,
            joined_on=now - datetime.timedelta(days=random.randint(60, 700)),
            risk_tier="low" if i % 10 != 0 else "medium",
            kyc_status="verified",
        )
        await db.merge(merchant)

        # Device
        battery = random.randint(35, 100) if i % 15 != 0 else random.randint(8, 18)
        last_seen = now - datetime.timedelta(minutes=random.randint(1, 30))
        device = Device(
            id=device_id,
            merchant_id=m_id,
            model="Soundbox v3 4G",
            battery=battery,
            network=random.choice(["4G Airtel", "4G Jio", "4G Vi"]),
            last_seen=last_seen,
            firmware="v2.4.1",
        )
        await db.merge(device)

        # 90-day transactions and daily settlements (sample per merchant)
        monthly_vol = 0.0
        for day_offset in range(5):  # Recent 5 days transactions
            day_date = today - datetime.timedelta(days=day_offset)
            daily_total = 0.0
            num_txns = random.randint(3, 8)
            for t_idx in range(num_txns):
                amount = float(random.randint(40, 1500))
                is_failed = random.random() < 0.08
                status = "failed" if is_failed else "success"
                failure_reason = random.choice(["bank_timeout", "insufficient_balance", "technical_decline"]) if is_failed else None

                txn = Transaction(
                    txn_id=f"txn_{m_id}_{day_offset}_{t_idx}",
                    merchant_id=m_id,
                    amount=amount,
                    status=status,
                    mode="upi",
                    failure_reason=failure_reason,
                    ts=now - datetime.timedelta(days=day_offset, hours=random.randint(1, 12)),
                )
                await db.merge(txn)
                if not is_failed:
                    daily_total += amount

            monthly_vol += daily_total * 6  # Projected monthly volume

            # Settlement for that day
            fee_amount = round(daily_total * 0.015, 2)
            actual_amount = max(0.0, daily_total - fee_amount)
            settlement_id = f"set_{m_id}_{day_date.isoformat()}"

            settlement = Settlement(
                id=settlement_id,
                merchant_id=m_id,
                date=day_date.isoformat(),
                expected=daily_total,
                actual=actual_amount,
                gap=fee_amount,
            )
            await db.merge(settlement)

            if fee_amount > 0:
                await db.merge(SettlementItem(
                    settlement_id=settlement_id,
                    type="fee",
                    amount=fee_amount,
                ))

        # Loan Profile
        await db.merge(LoanProfile(
            merchant_id=m_id,
            monthly_volume=monthly_vol,
            vintage_months=random.randint(4, 24),
            score=random.randint(680, 820),
            eligible_limit=float(random.choice([25000, 50000, 75000, 100000])),
        ))

    # 6. Load Kaggle & OpenFlights Datasets (airports, routes, domestic flights, PaySim transactions)
    await load_airports(db, "airports.txt")
    await load_flights(db, "price_prediction_datatset/Clean_Dataset.csv", per_route=12)
    await load_routes(db, "routes.txt", limit=100)
    await load_paysim_transactions(db, sample_size=100)

    await db.commit()
    logger.info("Database seeding completed successfully.")
