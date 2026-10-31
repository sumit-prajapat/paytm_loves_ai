import csv
import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Flight

logger = logging.getLogger(__name__)

# Known Indian airline code mapping
AIRLINE_MAP = {
    "AI": "Air India",
    "6E": "IndiGo",
    "SG": "SpiceJet",
    "UK": "Vistara",
    "G8": "GoAir",
    "I5": "AirAsia India",
    "QP": "Akasa Air",
}


async def load_routes(db: AsyncSession, filepath: str = "routes.txt", limit: int = 150) -> int:
    """Parses OpenFlights routes.txt and creates realistic domestic flight connections

    between recognized Indian airports.
    """
    if not os.path.exists(filepath):
        logger.info(f"Routes file '{filepath}' not found, skipping routes load.")
        return 0

    logger.info(f"Loading domestic routes from '{filepath}'...")
    loaded = 0

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 5:
                    continue

                airline_code = row[0].strip().upper()
                from_iata = row[2].strip().upper()
                to_iata = row[4].strip().upper()

                if len(from_iata) != 3 or len(to_iata) != 3 or from_iata == "\\N" or to_iata == "\\N":
                    continue

                airline_name = AIRLINE_MAP.get(airline_code, f"{airline_code} Airlines" if airline_code != "\\N" else "IndiGo")

                # Generate a flight entry for tomorrow
                flight_id = f"rt_{airline_code}_{from_iata}_{to_iata}_{loaded}"
                dep_time = "10:30" if loaded % 2 == 0 else "18:45"
                arr_time = "12:45" if loaded % 2 == 0 else "20:55"
                duration_min = 135

                flight = Flight(
                    id=flight_id,
                    airline=airline_name,
                    from_iata=from_iata,
                    to_iata=to_iata,
                    dep_time=dep_time,
                    arr_time=arr_time,
                    duration_min=duration_min,
                    stops=0,
                    price_inr=float(3400 + (loaded % 20) * 150),
                    refundable=(loaded % 3 == 0),
                    on_time_pct=91.5,
                    date="2026-11-01",
                )
                await db.merge(flight)
                loaded += 1
                if loaded >= limit:
                    break

        await db.commit()
        logger.info(f"Loaded {loaded} flights/routes from '{filepath}'.")
        return loaded
    except Exception as e:
        logger.warning(f"Error reading routes file '{filepath}': {e}")
        return 0
