import csv
import datetime
import logging
import os
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Flight

logger = logging.getLogger(__name__)

CITY_TO_IATA = {
    "Delhi": "DEL",
    "Mumbai": "BOM",
    "Bangalore": "BLR",
    "Kolkata": "CCU",
    "Hyderabad": "HYD",
    "Chennai": "MAA",
}

TIME_SLOT_HOURS = {
    "Early_Morning": ("06:00", "08:15"),
    "Morning": ("09:30", "11:45"),
    "Afternoon": ("14:00", "16:15"),
    "Evening": ("18:30", "20:45"),
    "Night": ("22:00", "00:15"),
    "Late_Night": ("01:30", "03:45"),
}


def get_demo_dates() -> tuple[str, str]:
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    day_after = today + datetime.timedelta(days=2)
    return tomorrow.isoformat(), day_after.isoformat()


def build_guaranteed_demo_flights(tomorrow_str: str, day_after_str: str) -> list[Flight]:
    """Guaranteed deterministic flights for the live hackathon demo (Delhi -> Mumbai tomorrow)."""
    return [
        # DEL -> BOM Tomorrow Evening (The Hero Trip)
        Flight(
            id="fl_demo_cheap",
            airline="IndiGo",
            from_iata="DEL",
            to_iata="BOM",
            dep_time="18:00",
            arr_time="20:40",
            duration_min=160,
            stops=0,
            price_inr=4200.0,
            refundable=False,
            on_time_pct=91.5,
            date=tomorrow_str,
        ),
        Flight(
            id="fl_demo_fast",
            airline="Air India",
            from_iata="DEL",
            to_iata="BOM",
            dep_time="19:15",
            arr_time="21:10",
            duration_min=115,
            stops=0,
            price_inr=5600.0,
            refundable=True,
            on_time_pct=88.0,
            date=tomorrow_str,
        ),
        Flight(
            id="fl_demo_best",
            airline="Vistara",
            from_iata="DEL",
            to_iata="BOM",
            dep_time="18:45",
            arr_time="20:50",
            duration_min=125,
            stops=0,
            price_inr=4600.0,  # ₹400 more than cheapest, 35 mins faster, free cancellation
            refundable=True,
            on_time_pct=96.5,
            date=tomorrow_str,
        ),
        Flight(
            id="fl_demo_onestop",
            airline="SpiceJet",
            from_iata="DEL",
            to_iata="BOM",
            dep_time="16:30",
            arr_time="21:45",
            duration_min=315,
            stops=1,
            price_inr=3700.0,
            refundable=False,
            on_time_pct=82.0,
            date=tomorrow_str,
        ),
        Flight(
            id="fl_demo_morning",
            airline="IndiGo",
            from_iata="DEL",
            to_iata="BOM",
            dep_time="08:00",
            arr_time="10:15",
            duration_min=135,
            stops=0,
            price_inr=4800.0,
            refundable=False,
            on_time_pct=94.0,
            date=tomorrow_str,
        ),
        Flight(
            id="fl_demo_afternoon",
            airline="Akasa Air",
            from_iata="DEL",
            to_iata="BOM",
            dep_time="14:15",
            arr_time="16:35",
            duration_min=140,
            stops=0,
            price_inr=4400.0,
            refundable=False,
            on_time_pct=90.0,
            date=tomorrow_str,
        ),
        # Flexible date comparison (Day after tomorrow morning - ₹1100 sasta)
        Flight(
            id="fl_demo_flex_cheaper",
            airline="IndiGo",
            from_iata="DEL",
            to_iata="BOM",
            dep_time="07:30",
            arr_time="09:45",
            duration_min=135,
            stops=0,
            price_inr=3500.0,  # ₹1100 cheaper than Vistara best pick!
            refundable=False,
            on_time_pct=95.0,
            date=day_after_str,
        ),
        # Return BOM -> DEL
        Flight(
            id="fl_demo_return",
            airline="Vistara",
            from_iata="BOM",
            to_iata="DEL",
            dep_time="19:30",
            arr_time="21:45",
            duration_min=135,
            stops=0,
            price_inr=4900.0,
            refundable=True,
            on_time_pct=95.0,
            date=tomorrow_str,
        ),
    ]


@lru_cache(maxsize=4)
def _parse_csv(csv_path: str, per_route: int) -> tuple[dict, ...]:
    """Parse once per process (the CSV has ~300k rows); keep at most `per_route` economy fares
    per Indian city pair."""
    rows: list[dict] = []
    if not os.path.exists(csv_path):
        return ()
    per_route_count: dict[tuple[str, str], int] = {}
    try:
        with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
            for row in csv.DictReader(f):
                src = row.get("source_city", "").strip()
                dst = row.get("destination_city", "").strip()
                route = (src, dst)
                if (row.get("class", "Economy") != "Economy" or src not in CITY_TO_IATA
                        or dst not in CITY_TO_IATA or src == dst or per_route_count.get(route, 0) >= per_route):
                    continue
                try:
                    duration_min = int(float(row.get("duration", 2.2)) * 60)
                    price = float(row.get("price", 5000))
                except ValueError:
                    continue
                per_route_count[route] = per_route_count.get(route, 0) + 1
                airline = row.get("airline", "Air India").replace("_", " ")
                stops_str = row.get("stops", "zero").lower()
                rows.append({
                    "airline": airline,
                    "from_iata": CITY_TO_IATA[src],
                    "to_iata": CITY_TO_IATA[dst],
                    "dep_time": TIME_SLOT_HOURS.get(row.get("departure_time", ""), ("09:00", "11:00"))[0],
                    "arr_time": TIME_SLOT_HOURS.get(row.get("arrival_time", ""), ("12:00", "14:00"))[1],
                    "duration_min": duration_min,
                    "stops": 0 if "zero" in stops_str else (1 if "one" in stops_str else 2),
                    "price_inr": price,
                    "refundable": "Vistara" in airline or "Air India" in airline,
                    "odd": per_route_count[route] % 2 == 1,
                })
    except OSError as exc:
        logger.warning("Could not read flights CSV: %s", exc)
    return tuple(rows)


async def load_flights(
    db: AsyncSession,
    csv_path: str = "price_prediction_datatset/Clean_Dataset.csv",
    per_route: int = 12,
) -> int:
    """Loads Kaggle fares for ALL Indian city pairs in the dataset (SIMULATED schedule),
    capped per route and spread over tomorrow / day after, plus guaranteed demo flights."""
    tomorrow_str, day_after_str = get_demo_dates()
    demo_flights = build_guaranteed_demo_flights(tomorrow_str, day_after_str)
    for fl in demo_flights:
        await db.merge(fl)
    rows = _parse_csv(csv_path, per_route)
    for i, r in enumerate(rows):
        fields = {k: v for k, v in r.items() if k != "odd"}
        await db.merge(Flight(id=f"fl_kg_{i}", on_time_pct=88.0 + (i % 10),
                              date=tomorrow_str if r["odd"] else day_after_str, **fields))
    await db.commit()
    total = len(demo_flights) + len(rows)
    logger.info("Loaded %s flights (SIMULATED schedule)", total)
    return total
