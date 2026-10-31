import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Device, Festival, Refund, Settlement


class AnomalyService:
    """Scans for operational anomalies across settlements, devices, festivals, and refunds."""

    @staticmethod
    async def scan_anomalies(db: AsyncSession) -> list[dict[str, Any]]:
        anomalies = []
        today = datetime.date.today()

        # 1. Settlement shortfalls
        stmt_set = select(Settlement).where(Settlement.gap > 0)
        res_set = await db.execute(stmt_set)
        for s in res_set.scalars().all():
            anomalies.append({
                "type": "settlement_short",
                "merchant_id": s.merchant_id,
                "gap": s.gap,
                "date": s.date,
            })

        # 2. Soundbox low battery or offline
        stmt_dev = select(Device).where(Device.battery <= 20)
        res_dev = await db.execute(stmt_dev)
        for d in res_dev.scalars().all():
            anomalies.append({
                "type": "soundbox_low_battery",
                "device_id": d.id,
                "merchant_id": d.merchant_id,
                "battery": d.battery,
            })

        # 3. Overdue refunds (> 7 days)
        stmt_ref = select(Refund).where(Refund.status == "overdue")
        res_ref = await db.execute(stmt_ref)
        for r in res_ref.scalars().all():
            anomalies.append({
                "type": "refund_overdue",
                "refund_id": r.id,
                "txn_id": r.txn_id,
                "bank_ref": r.bank_ref,
            })

        # 4. Festival check (upcoming within 10 days)
        stmt_fest = select(Festival)
        res_fest = await db.execute(stmt_fest)
        for f in res_fest.scalars().all():
            try:
                fest_date = datetime.date.fromisoformat(f.date)
                days_until = (fest_date - today).days
                if 0 <= days_until <= 14:
                    anomalies.append({
                        "type": "festival_approaching",
                        "festival_name": f.name,
                        "date": f.date,
                        "days_until": days_until,
                    })
                    break
            except Exception:
                pass

        return anomalies


anomaly_service = AnomalyService()
