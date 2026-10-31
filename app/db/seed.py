import datetime
import logging
import random

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.loaders.airports_loader import load_airports
from app.db.loaders.flights_loader import load_flights
from app.db.loaders.paysim_loader import load_paysim_transactions
from app.db.loaders.routes_loader import load_routes
from app.db.models import (
    Customer,
    Device,
    DeviceEvent,
    Dispute,
    Festival,
    LoanProfile,
    Merchant,
    Playbook,
    Policy,
    Refund,
    Settlement,
    SettlementItem,
    Transaction,
    User,
)
from app.core.security import hash_password
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

    # 2. Seed Festivals
    for fest in UPCOMING_FESTIVALS:
        await db.merge(Festival(
            date=fest["date"],
            name=fest["name"],
            region=fest["region"],
        ))

    # 3. Seed Initial Playbooks
    await db.merge(Playbook(
        id="pb_settlement_reconciled",
        issue_type="settlement_short",
        root_cause="refund_adjustment_and_fee",
        action="explain_breakdown_and_close_zero_ticket",
        conditions_json={"settlement_gap_matches_items": True},
        created_from_case="historical_resolution",
        times_used=14,
    ))
    await db.merge(Playbook(
        id="pb_soundbox_low_battery",
        issue_type="soundbox_offline",
        root_cause="battery_depleted",
        action="voice_instruction_connect_charger",
        conditions_json={"battery_below_pct": 20},
        created_from_case="historical_resolution",
        times_used=8,
    ))

    # 4. Seed HERO PERSONAS (Fixed forever)
    # Hero 1: Ramesh (Kirana, Hindi, Delhi)
    ramesh = Merchant(
        id="m_ramesh",
        name="Ramesh Kirana Store",
        city="Delhi",
        state="Delhi",
        language="hi",
        business_type="kirana",
        device_id="soundbox_ramesh_01",
        joined_on=now - datetime.timedelta(days=365),
        risk_tier="low",
        kyc_status="verified",
    )
    await db.merge(ramesh)

    soundbox_ramesh = Device(
        id="soundbox_ramesh_01",
        merchant_id="m_ramesh",
        model="Soundbox v3 4G",
        battery=12,  # Low battery! Triggers low battery flow
        network="4G Airtel",
        last_seen=now - datetime.timedelta(minutes=15),
        firmware="v2.4.1",
    )
    await db.merge(soundbox_ramesh)

    await db.merge(DeviceEvent(
        device_id="soundbox_ramesh_01",
        ts=now - datetime.timedelta(hours=1),
        event="low_battery",
    ))

    # Ramesh Settlement: Short by exactly 1800 (1200 refund + 600 fees)
    ramesh_settlement = Settlement(
        id="set_ramesh_today",
        merchant_id="m_ramesh",
        date=today.isoformat(),
        expected=24500.0,
        actual=22700.0,
        gap=1800.0,
    )
    await db.merge(ramesh_settlement)

    await db.merge(SettlementItem(
        settlement_id="set_ramesh_today",
        type="refund_adjustment",
        amount=1200.0,
    ))
    await db.merge(SettlementItem(
        settlement_id="set_ramesh_today",
        type="fee",
        amount=600.0,
    ))

    # Ramesh Loan Profile: eligible up to 100,000 INR
    await db.merge(LoanProfile(
        merchant_id="m_ramesh",
        monthly_volume=185000.0,
        vintage_months=14,
        score=780,
        eligible_limit=100000.0,
    ))

    # Hero 2: Sunita (Tailor, Marathi, Mumbai) with overdue refund
    sunita = Merchant(
        id="m_sunita",
        name="Sunita Tailors",
        city="Mumbai",
        state="Maharashtra",
        language="mr",
        business_type="tailor",
        device_id="soundbox_sunita_01",
        joined_on=now - datetime.timedelta(days=200),
        risk_tier="low",
        kyc_status="verified",
    )
    await db.merge(sunita)

    await db.merge(Device(
        id="soundbox_sunita_01",
        merchant_id="m_sunita",
        model="Soundbox v3",
        battery=85,
        network="4G Jio",
        last_seen=now - datetime.timedelta(minutes=2),
        firmware="v2.4.1",
    ))

    # Sunita's failed transaction and overdue refund
    sunita_txn = Transaction(
        txn_id="txn_sunita_refund_01",
        merchant_id="m_sunita",
        amount=1450.0,
        status="failed",
        mode="upi",
        failure_reason="bank_timeout",
        ts=now - datetime.timedelta(days=9),
    )
    await db.merge(sunita_txn)

    sunita_refund = Refund(
        id="ref_sunita_overdue_01",
        txn_id="txn_sunita_refund_01",
        status="overdue",  # Overdue beyond 7 days!
        initiated_at=now - datetime.timedelta(days=9),
        expected_by=now - datetime.timedelta(days=2),
        bank_ref="REF9876543210IN",
    )
    await db.merge(sunita_refund)

    # Hero 3: Merchant with disputed chargeback (high impact, for escalation)
    disputed_merchant = Merchant(
        id="m_disputed",
        name="Gupta Electronics",
        city="Lucknow",
        state="Uttar Pradesh",
        language="hi",
        business_type="electronics",
        device_id="soundbox_gupta_01",
        joined_on=now - datetime.timedelta(days=120),
        risk_tier="medium",
        kyc_status="verified",
    )
    await db.merge(disputed_merchant)

    dispute_txn = Transaction(
        txn_id="txn_chargeback_99",
        merchant_id="m_disputed",
        amount=6500.0,  # Exceeds threshold of 5000 INR
        status="success",
        mode="card",
        failure_reason=None,
        ts=now - datetime.timedelta(days=3),
    )
    await db.merge(dispute_txn)

    await db.merge(Dispute(
        id="disp_case_7701",
        txn_id="txn_chargeback_99",
        amount=6500.0,
        reason="Cardholder claims card was stolen and unauthorized transaction occurred at store",
        status="open",
        deadline=now + datetime.timedelta(days=4),
        evidence_json={"invoice_required": True, "cctv_allowed": True},
    ))

    # Hero Customers / Travellers: Arjun & Meena Aunty
    await db.merge(Customer(
        id="c_arjun",
        name="Arjun Sharma",
        home_city="Delhi",
        language="en",
        travel_history=[{"from": "DEL", "to": "BOM", "airline": "IndiGo", "price": 4100}],
    ))

    await db.merge(Customer(
        id="c_meena",
        name="Meena Devi (Meena Aunty)",
        home_city="Delhi",
        language="hi",
        travel_history=[{"from": "DEL", "to": "VNS", "airline": "Air India"}],
    ))

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
    await load_flights(db, "price_prediction_datatset/Clean_Dataset.csv", limit=300)
    await load_routes(db, "routes.txt", limit=100)
    await load_paysim_transactions(db, sample_size=100)

    # 7. Seed Demo Users for Authentication & RBAC (Simulated Demo Credentials)
    demo_users = [
        User(
            id="usr_ramesh",
            username="merchant_ramesh",
            password_hash=hash_password("DemoPass@123"),
            role="merchant",
            merchant_id="m_ramesh",
            customer_id=None,
        ),
        User(
            id="usr_sunita",
            username="merchant_sunita",
            password_hash=hash_password("DemoPass@123"),
            role="merchant",
            merchant_id="m_sunita",
            customer_id=None,
        ),
        User(
            id="usr_arjun",
            username="traveller_arjun",
            password_hash=hash_password("DemoPass@123"),
            role="traveller",
            merchant_id=None,
            customer_id="c_arjun",
        ),
        User(
            id="usr_ops",
            username="ops_agent_1",
            password_hash=hash_password("DemoPass@123"),
            role="ops_agent",
            merchant_id=None,
            customer_id=None,
        ),
        User(
            id="usr_admin",
            username="admin_user",
            password_hash=hash_password("AdminPass@123"),
            role="admin",
            merchant_id=None,
            customer_id=None,
        ),
    ]
    for u in demo_users:
        await db.merge(u)

    await db.commit()
    logger.info("Database seeding completed successfully.")
