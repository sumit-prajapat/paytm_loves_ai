import csv
import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Airport

logger = logging.getLogger(__name__)

# Fallback prominent Indian airports if file is not found
FALLBACK_AIRPORTS = [
    {"iata": "DEL", "name": "Indira Gandhi International Airport", "city": "Delhi", "lat": 28.5562, "lon": 77.1000},
    {"iata": "BOM", "name": "Chhatrapati Shivaji Maharaj International Airport", "city": "Mumbai", "lat": 19.0896, "lon": 72.8656},
    {"iata": "BLR", "name": "Kempegowda International Airport", "city": "Bangalore", "lat": 13.1986, "lon": 77.7066},
    {"iata": "MAA", "name": "Chennai International Airport", "city": "Chennai", "lat": 12.9941, "lon": 80.1709},
    {"iata": "CCU", "name": "Netaji Subhash Chandra Bose International Airport", "city": "Kolkata", "lat": 22.6547, "lon": 88.4467},
    {"iata": "HYD", "name": "Rajiv Gandhi International Airport", "city": "Hyderabad", "lat": 17.2403, "lon": 78.4294},
    {"iata": "AMD", "name": "Sardar Vallabhbhai Patel International Airport", "city": "Ahmedabad", "lat": 23.0772, "lon": 72.6347},
    {"iata": "PNQ", "name": "Pune Airport", "city": "Pune", "lat": 18.5822, "lon": 73.9197},
    {"iata": "GOI", "name": "Dabolim Airport", "city": "Goa", "lat": 15.3808, "lon": 73.8314},
    {"iata": "JAI", "name": "Jaipur International Airport", "city": "Jaipur", "lat": 26.8242, "lon": 75.8122},
    {"iata": "LKO", "name": "Chaudhary Charan Singh International Airport", "city": "Lucknow", "lat": 26.7606, "lon": 80.8893},
    {"iata": "COK", "name": "Cochin International Airport", "city": "Kochi", "lat": 10.1518, "lon": 76.4019},
    {"iata": "PAT", "name": "Jay Prakash Narayan Airport", "city": "Patna", "lat": 25.5913, "lon": 85.0880},
    {"iata": "VNS", "name": "Lal Bahadur Shastri International Airport", "city": "Varanasi", "lat": 25.4524, "lon": 82.8593},
    {"iata": "BBI", "name": "Biju Patnaik Airport", "city": "Bhubaneswar", "lat": 20.2444, "lon": 85.8178},
    {"iata": "IXC", "name": "Chandigarh International Airport", "city": "Chandigarh", "lat": 30.6735, "lon": 76.7885},
    {"iata": "GAU", "name": "Lokpriya Gopinath Bordoloi International Airport", "city": "Guwahati", "lat": 26.1061, "lon": 91.5859},
]


async def load_airports(db: AsyncSession, filepath: str = "airports.txt") -> int:
    """Loads Indian airports from OpenFlights airports.dat/txt or falls back cleanly."""
    airports_to_add: dict[str, Airport] = {}

    if os.path.exists(filepath):
        logger.info(f"Loading airports from {filepath}")
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                for row in reader:
                    # OpenFlights format: id, name, city, country, iata, icao, lat, lon
                    if len(row) >= 8:
                        country = row[3].strip()
                        iata = row[4].strip().upper()
                        if country == "India" and iata and iata != "\\N" and len(iata) == 3:
                            name = row[1].strip()
                            city = row[2].strip()
                            try:
                                lat = float(row[6])
                                lon = float(row[7])
                            except ValueError:
                                continue
                            airports_to_add[iata] = Airport(
                                iata=iata,
                                name=name,
                                city=city,
                                lat=lat,
                                lon=lon,
                            )
        except Exception as e:
            logger.warning(f"Failed parsing {filepath}: {e}, falling back to built-in Indian airports")

    # If file was empty or parsed fewer than 5 airports, merge fallbacks
    for fb in FALLBACK_AIRPORTS:
        if fb["iata"] not in airports_to_add:
            airports_to_add[fb["iata"]] = Airport(
                iata=fb["iata"],
                name=fb["name"],
                city=fb["city"],
                lat=fb["lat"],
                lon=fb["lon"],
            )

    for airport in airports_to_add.values():
        await db.merge(airport)

    await db.commit()
    logger.info(f"Loaded {len(airports_to_add)} Indian airports into database")
    return len(airports_to_add)
