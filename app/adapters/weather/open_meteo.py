import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class WeatherAdapter:
    """Free weather adapter using Open-Meteo with fallback to typical Indian weather."""

    @staticmethod
    async def get_weather(lat: float, lon: float) -> dict[str, Any]:
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    cw = data.get("current_weather", {})
                    return {
                        "temperature_c": cw.get("temperature", 28.0),
                        "windspeed_kmh": cw.get("windspeed", 12.0),
                        "weathercode": cw.get("weathercode", 0),
                        "condition": "Clear / Pleasant",
                    }
        except Exception as e:
            logger.warning(f"Open-Meteo weather fetch failed: {e}. FALLBACK USED")

        return {
            "temperature_c": 28.5,
            "windspeed_kmh": 10.0,
            "condition": "Pleasant / Clear",
            "source": "fallback",
        }


weather_adapter = WeatherAdapter()
