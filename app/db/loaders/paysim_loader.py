import csv
import datetime
import logging
import os
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Dispute, Transaction

logger = logging.getLogger(__name__)

PAY_SIM_PATH = os.path.join("payslim transaction dataset", "PS_20174392719_1491204439457_log.csv")


async def load_paysim_transactions(
    db: AsyncSession,
    filepath: str = PAY_SIM_PATH,
    sample_size: int = 150,
) -> int:
    """Streams realistic financial payment and transfer records from the Kaggle PaySim dataset.

    Populates genuine merchant transactions and dispute cases into SQLite.
    """
    if not os.path.exists(filepath):
        logger.info(f"PaySim dataset not found at '{filepath}', skipping PaySim ingestion.")
        return 0

    logger.info(f"Streaming {sample_size} real transaction records from PaySim '{filepath}'...")
    loaded = 0
    now = datetime.datetime.now(datetime.timezone.utc)

    merchants = ["m_ramesh", "m_sunita", "m_gupta_electronics", "m_disputed"]

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                txn_type = row.get("type", "").upper()
                if txn_type not in ("PAYMENT", "TRANSFER"):
                    continue

                raw_amount = float(row.get("amount", 0.0))
                # Normalize retail transaction scale for Indian kirana demonstration
                amount = round(raw_amount if raw_amount < 50000 else (raw_amount % 12000) + 120, 2)
                is_fraud = int(row.get("isFraud", 0)) == 1

                m_id = merchants[loaded % len(merchants)]
                txn_id = f"txn_paysim_{loaded:04d}"
                status = "failed" if is_fraud else "success"
                failure_reason = "security_fraud_flag" if is_fraud else None

                txn = Transaction(
                    txn_id=txn_id,
                    merchant_id=m_id,
                    amount=amount,
                    status=status,
                    mode="upi",
                    failure_reason=failure_reason,
                    ts=now - datetime.timedelta(hours=loaded * 2),
                )
                await db.merge(txn)

                # If flagged as fraud in PaySim, create a realistic dispute case
                if is_fraud and m_id == "m_disputed":
                    dispute = Dispute(
                        id=f"dsp_paysim_{loaded:04d}",
                        txn_id=txn_id,
                        merchant_id=m_id,
                        amount=amount,
                        reason="Customer claims unauthorized transaction / chargeback",
                        status="open",
                        sla_deadline=now + datetime.timedelta(hours=48),
                    )
                    await db.merge(dispute)

                loaded += 1
                if loaded >= sample_size:
                    break

        await db.commit()
        logger.info(f"Loaded {loaded} PaySim Kaggle transactions into database.")
        return loaded
    except Exception as e:
        logger.warning(f"Error streaming PaySim dataset '{filepath}': {e}")
        return 0
