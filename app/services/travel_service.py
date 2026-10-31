"""Deterministic travel search, scoring and human review-and-pay handoff (R1, R3)."""
from __future__ import annotations

import datetime
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.cache import cache
from app.db.models import Flight
from app.i18n import t
from app.i18n.numbers import format_inr, money

WINDOW_HOURS = {"morning": (5, 12), "afternoon": (12, 17), "evening": (17, 21), "night": (21, 24)}
WEIGHTS = {  # price, duration, window fit, stops, refundable, on-time
    "cheap": (0.50, 0.15, 0.10, 0.10, 0.05, 0.10),
    "fast": (0.15, 0.45, 0.10, 0.15, 0.05, 0.10),
    "comfort": (0.15, 0.20, 0.10, 0.25, 0.15, 0.15),
    "balanced": (0.30, 0.25, 0.15, 0.10, 0.10, 0.10),
}


def _flight_dict(f: Flight) -> dict[str, Any]:
    return {"flight_id": f.id, "airline": f.airline, "from": f.from_iata, "to": f.to_iata, "date": f.date,
            "dep_time": f.dep_time, "arr_time": f.arr_time, "duration_min": f.duration_min, "stops": f.stops,
            "price_inr": f.price_inr, "refundable": f.refundable, "on_time_pct": f.on_time_pct}


def time_fit(dep_time: str, window: str | None) -> float:
    if not window or window not in WINDOW_HOURS:
        return 1.0
    try:
        hour = int(dep_time.split(":")[0])
    except (ValueError, IndexError):
        return 0.5
    start, end = WINDOW_HOURS[window]
    if start <= hour < end:
        return 1.0
    diff = min(abs(hour - start), abs(hour - end))
    return max(0.2, 1.0 - diff * 0.15)


def score_flight(f: dict[str, Any], bounds: dict[str, float], preference: str, window: str | None) -> dict[str, float]:
    w_p, w_d, w_w, w_s, w_r, w_o = WEIGHTS.get(preference, WEIGHTS["balanced"])
    price_norm = 1.0 - (f["price_inr"] - bounds["min_p"]) / max(bounds["max_p"] - bounds["min_p"], 1.0)
    dur_norm = 1.0 - (f["duration_min"] - bounds["min_d"]) / max(bounds["max_d"] - bounds["min_d"], 1.0)
    parts = {
        "price_score": w_p * price_norm,
        "duration_score": w_d * dur_norm,
        "time_fit_score": w_w * time_fit(f["dep_time"], window),
        "stops_score": w_s * (1.0 if f["stops"] == 0 else 0.5 if f["stops"] == 1 else 0.0),
        "refundable_score": w_r * (1.0 if f["refundable"] else 0.0),
        "ontime_score": w_o * min(max(f["on_time_pct"] / 100.0, 0.0), 1.0),
    }
    parts = {k: round(v, 3) for k, v in parts.items()}
    parts["total_score"] = round(sum(parts.values()), 3)
    return parts


async def search_flights(db: AsyncSession, origin: str, destination: str, date: str) -> list[dict[str, Any]]:
    """One query covering date-1..date+1 (flexible dates). Cached by route+date (R12)."""
    key = f"flights:{origin}:{destination}:{date}"
    hit = cache.get(key)
    if hit is not None:
        return hit
    d = datetime.date.fromisoformat(date)
    days = [(d + datetime.timedelta(days=k)).isoformat() for k in (-1, 0, 1)]
    rows = (await db.execute(
        select(Flight).where(Flight.from_iata == origin, Flight.to_iata == destination, Flight.date.in_(days))
    )).scalars().all()
    flights = [_flight_dict(f) for f in rows]
    cache.set(key, flights, get_settings().FLIGHT_SEARCH_CACHE_TTL_SECONDS)
    return flights


def rank(flights: list[dict[str, Any]], requested_date: str, preference: str, window: str | None,
         elder: bool = False) -> dict[str, Any]:
    on_date = [f for f in flights if f["date"] == requested_date]
    date_adjusted = False
    pool = on_date
    if not pool and flights:
        date_adjusted = True
        req = datetime.date.fromisoformat(requested_date)
        nearest = min({f["date"] for f in flights}, key=lambda x: abs((datetime.date.fromisoformat(x) - req).days))
        pool = [f for f in flights if f["date"] == nearest]
    if not pool:
        return {"options": [], "recommended": None, "date_adjusted": False, "actual_date": requested_date}
    if elder:
        preference = "comfort"
    bounds = {"min_p": min(f["price_inr"] for f in pool), "max_p": max(f["price_inr"] for f in pool),
              "min_d": min(f["duration_min"] for f in pool), "max_d": max(f["duration_min"] for f in pool)}
    scored = [{**f, "score_breakdown": score_flight(f, bounds, preference, window)} for f in pool]
    # Deterministic tie-breaks: score, then price, then flight id
    scored.sort(key=lambda f: (-f["score_breakdown"]["total_score"], f["price_inr"], f["flight_id"]))
    cheapest = min(scored, key=lambda f: (f["price_inr"], f["duration_min"], f["flight_id"]))
    fastest = min(scored, key=lambda f: (f["duration_min"], f["price_inr"], f["flight_id"]))
    best = scored[0]
    options = [{"label": "CHEAPEST", **cheapest}, {"label": "FASTEST", **fastest}, {"label": "BEST_BALANCE", **best}]
    if elder:
        options = [{"label": "BEST_BALANCE", **best}]
    return {"options": options, "recommended": best, "cheapest": cheapest, "date_adjusted": date_adjusted,
            "actual_date": pool[0]["date"], "candidates": len(pool), "preference": preference}


def reason_text(ranked: dict[str, Any], lang: str) -> tuple[str, dict[str, Any]]:
    best, cheapest = ranked["recommended"], ranked["cheapest"]
    price_diff = round(best["price_inr"] - cheapest["price_inr"], 2)
    minutes_saved = cheapest["duration_min"] - best["duration_min"]
    facts = {"price": best["price_inr"], "price_diff": price_diff, "minutes_saved": minutes_saved,
             "airline": best["airline"]}
    if price_diff <= 0:
        text = t("travel.reason.cheapest_is_best", lang, airline=best["airline"], price=format_inr(best["price_inr"]))
    elif minutes_saved > 0:
        text = t("travel.reason.costlier_faster", lang, airline=best["airline"], price=format_inr(best["price_inr"]),
                 price_diff=format_inr(price_diff), minutes_saved=minutes_saved)
    else:
        text = t("travel.reason.costlier_better_score", lang, airline=best["airline"],
                 price=format_inr(best["price_inr"]), price_diff=format_inr(price_diff))
    if best["refundable"]:
        text += t("travel.reason.refundable_suffix", lang)
    return text, facts


def risk_flags(option: dict[str, Any]) -> list[str]:
    flags = []
    if not option["refundable"]:
        flags.append("non_refundable")
    if option["stops"] > 0:
        flags.append("has_stops")
    return flags


def booking_summary(option: dict[str, Any], passenger_name: str) -> dict[str, Any]:
    """Human-only review & pay handoff (R3). The AI never pays or confirms a booking."""
    order_id = f"ord_{uuid.uuid4().hex[:12]}"
    base = get_settings().PUBLIC_BASE_URL.rstrip("/")
    return {
        "booking_draft_id": f"bk_draft_{uuid.uuid4().hex[:10]}",
        "status": "ready_for_human_review",
        "passenger_name": passenger_name,
        "flight": {k: option[k] for k in ("flight_id", "airline", "from", "to", "date", "dep_time", "arr_time",
                                          "duration_min", "stops", "refundable")},
        "fare": money(option["price_inr"]),
        "convenience_fee": money(0),
        "total_payable": money(option["price_inr"]),
        "cancellation_policy": "refundable" if option["refundable"] else "non_refundable",
        "risk_flags": risk_flags(option),
        "order_id": order_id,
        "payment_link": f"{base}/api/v1/payments/mock-checkout/{order_id}",
        "human_action_required": "Review the details and pay yourself with your UPI PIN. Saarthi never pays.",
    }
