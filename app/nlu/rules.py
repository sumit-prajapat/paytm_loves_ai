"""Tier 0 intent classification and slot extraction (deterministic, no LLM, R12).

Handles English, Roman Hindi (Hinglish) and Devanagari Hindi, typos (fuzzy match on longer
words), and matches on whole tokens/phrases only (so "now" never matches "no" and
"shopping" never matches "pin").
"""
from __future__ import annotations

import datetime
import difflib
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

# Intents the rest of the system understands (the LLM is constrained to this list too).
INTENTS = (
    "settlement_short",
    "soundbox_offline",
    "refund_status",
    "payment_failed",
    "chargeback_dispute",
    "loan_emi_query",
    "loan_apply",
    "loan_approve_request",
    "decline_offer",
    "travel_flight_request",
    "travel_status",
    "pulse_request",
    "advice_request",
    "raise_issue",
    "payment_request",
    "greeting",
    "unknown",
)

_PUNCT_RE = re.compile(r"[^\wऀ-ॿ₹.,:/-]+|[।॥]")


def normalize(text: str) -> str:
    text = text.lower().replace("‍", "").replace("‌", "")
    # Drop the Devanagari nukta so "आवाज़" == "आवाज" and "उड़ान" == "उडान"
    text = unicodedata.normalize("NFC", unicodedata.normalize("NFD", text).replace("़", ""))
    text = _PUNCT_RE.sub(" ", text)
    text = re.sub(r"(?<!\d)[.,:/-]|[.,:/-](?!\d)", " ", text)
    return re.sub(r"\s+", " ", text).strip()


@lru_cache(maxsize=4096)
def _norm_phrase(phrase: str) -> str:
    return normalize(phrase)


def _has(norm: str, phrase: str) -> bool:
    return f" {_norm_phrase(phrase)} " in f" {norm} "


# ---------------------------------------------------------------------------
# Lexicons: phrase -> weight. Devanagari entries are pre-normalised (no nukta).
# ---------------------------------------------------------------------------
LEXICON: dict[str, dict[str, float]] = {
    "settlement_short": {
        "settlement": 1.0, "settle": 0.8, "settlment": 1.0, "payout": 0.9, "सेटलमेंट": 1.0,
        "paisa kam": 1.0, "paise kam": 1.0, "kam aaya": 0.9, "kam aya": 0.9, "kam kyun": 0.6,
        "kam kyu": 0.6, "कम आया": 0.9, "कम क्यों": 0.6, "पैसे कम": 1.0, "पैसा कम": 1.0,
        "deduction": 1.0, "katauti": 1.0, "कटौती": 1.0, "cut gaya": 0.9, "kat gaya": 0.9,
        "short": 0.6, "less money": 0.9, "भुगतान कम": 1.0,
    },
    "soundbox_offline": {
        "soundbox": 1.0, "sound box": 1.0, "साउंडबॉक्स": 1.0, "साउंड बॉक्स": 1.0, "speaker": 0.8,
        "battery": 0.9, "बैटरी": 0.9, "awaaz nahi": 1.0, "awaz nahi": 1.0, "आवाज नहीं": 1.0,
        "bol nahi raha": 1.0, "बोल नहीं रहा": 1.0, "device": 0.7, "offline": 0.8, "ऑफलाइन": 0.8,
        "not speaking": 1.0, "not working": 0.5, "charge nahi": 0.9,
    },
    "refund_status": {
        "refund": 1.0, "रिफंड": 1.0, "रीफंड": 1.0, "paisa wapas": 1.0, "paise wapas": 1.0,
        "पैसा वापस": 1.0, "पैसे वापस": 1.0, "wapas kab": 0.9, "money back": 1.0,
    },
    "payment_failed": {
        "payment fail": 1.0, "payment failed": 1.0, "failed payment": 1.0, "fail ho gaya": 0.9,
        "fail hua": 0.9, "पेमेंट फेल": 1.0, "फेल हो गया": 0.9, "transaction failed": 1.0,
        "txn failed": 1.0, "declined": 0.6,
    },
    "chargeback_dispute": {
        "chargeback": 1.2, "charge back": 1.2, "चार्जबैक": 1.2, "dispute": 1.1, "विवाद": 1.1,
        "fraud claim": 1.1, "unauthorized": 0.8, "card stolen": 1.0,
    },
    "loan_emi_query": {
        "loan": 1.0, "लोन": 1.0, "emi": 1.0, "ईएमआई": 1.0, "karz": 0.9, "karza": 0.9, "कर्ज": 0.9,
        "interest": 0.6, "byaaj": 0.7, "byaj": 0.7, "ब्याज": 0.7, "working capital": 1.0,
    },
    "travel_flight_request": {
        "flight": 1.0, "flights": 1.0, "फ्लाइट": 1.0, "उड़ान": 1.0, "उडान": 1.0, "udaan": 0.9,
        "plane": 0.8, "air ticket": 1.0, "fly": 0.8, "हवाई": 0.8,
    },
    "travel_status": {
        "flight status": 1.2, "booking status": 1.2, "pnr": 1.0, "delay": 0.7, "late hai": 0.6,
        "gate": 0.5, "meri booking": 1.0, "my booking": 1.0, "बुकिंग": 0.8,
    },
    "pulse_request": {
        "pulse": 1.0, "business summary": 1.0, "aaj ka hisaab": 1.0, "hisaab": 0.8, "हिसाब": 0.8,
        "morning report": 1.0, "daily summary": 1.0,
    },
    "advice_request": {
        "festival": 1.0, "tyohar": 1.0, "tyohaar": 1.0, "त्योहार": 1.0, "diwali": 0.9, "दिवाली": 0.9,
        "holi": 0.8, "advice": 0.8, "salah": 0.8, "सलाह": 0.8, "tips": 0.6,
    },
    "raise_issue": {
        "complaint": 1.0, "shikayat": 1.0, "शिकायत": 1.0, "raise an issue": 1.2, "raise issue": 1.2,
        "ticket banao": 1.0, "ticket bana do": 1.0,
    },
    "greeting": {
        "hi": 0.6, "hello": 0.6, "namaste": 0.6, "नमस्ते": 0.6, "thanks": 0.6, "thank you": 0.6,
        "dhanyavaad": 0.6, "धन्यवाद": 0.6, "shukriya": 0.6, "good morning": 0.6, "good evening": 0.6,
        "kya haal": 0.6, "haal chal": 0.6, "kaise ho": 0.6, "aap kaun": 0.6, "who are you": 0.6, "शुभ प्रभात": 0.6,
    },
}

# High-priority patterns (checked before the scored lexicon).
DECLINE_PHRASES = (
    "nahi chahiye", "nahin chahiye", "nai chahiye", "नहीं चाहिए", "mat do", "मत दो", "no thanks",
    "not interested", "dont want", "don't want", "do not want", "baad mein", "बाद में",
    "offer mat", "mat bhejo", "मत भेजो", "no loan",
)
BARE_NEGATIONS = ("no", "nahi", "nahin", "नहीं", "na", "nope")
PAYMENT_REQUEST_PHRASES = (
    "pay for me", "payment kar do", "payment karo", "pay kar do", "pay karo", "पेमेंट कर दो",
    "भुगतान कर दो", "book it and pay", "book and pay", "confirm booking", "booking confirm",
    "confirm the booking", "paise bhej do", "transfer kar do", "payment bhi kar do",
    "khud pay", "pay it", "make the payment", "authorize and pay", "authorise and pay", "pay for this",
    "pay directly", "from my bank account", "wallet se pay", "account se pay", "debit my", "auto pay kar",
)
REFUND_DEMAND_PHRASES = (
    "refund me", "refund kar do", "refund de do", "refund karo", "रिफंड कर दो", "रिफंड दे दो",
    "issue refund", "refund now", "refund issue karo",
)
LOAN_APPROVE_PHRASES = (
    "approve my loan", "approve loan", "loan approve", "loan manzoor", "लोन मंजूर", "sanction my loan",
    "loan sanction",
)
LOAN_APPLY_PHRASES = (
    "apply", "apply karo", "apply kar do", "aavedan", "आवेदन", "haan apply", "yes apply",
)

_FUZZY_KEYWORDS = {
    word: intent
    for intent, words in LEXICON.items()
    for word in words
    if " " not in word and word.isascii() and len(word) >= 5
}

# ---------------------------------------------------------------------------
# Travel slots
# ---------------------------------------------------------------------------
CITY_TO_IATA = {
    "delhi": "DEL", "dilli": "DEL", "new delhi": "DEL", "दिल्ली": "DEL",
    "mumbai": "BOM", "bombay": "BOM", "मुंबई": "BOM", "मुम्बई": "BOM",
    "bangalore": "BLR", "bengaluru": "BLR", "banglore": "BLR", "बेंगलुरु": "BLR", "बैंगलोर": "BLR",
    "chennai": "MAA", "madras": "MAA", "चेन्नई": "MAA",
    "kolkata": "CCU", "calcutta": "CCU", "कोलकाता": "CCU",
    "hyderabad": "HYD", "हैदराबाद": "HYD",
    "goa": "GOI", "गोवा": "GOI",
    "pune": "PNQ", "पुणे": "PNQ",
    "ahmedabad": "AMD", "अहमदाबाद": "AMD",
    "jaipur": "JAI", "जयपुर": "JAI",
    "lucknow": "LKO", "लखनऊ": "LKO",
    "patna": "PAT", "पटना": "PAT",
    "kochi": "COK", "cochin": "COK", "कोच्चि": "COK",
    "varanasi": "VNS", "banaras": "VNS", "वाराणसी": "VNS",
    "chandigarh": "IXC", "चंडीगढ़": "IXC", "चंडीगढ": "IXC",
}
IATA_CODES = set(CITY_TO_IATA.values())

WINDOWS = {
    "morning": ("morning", "subah", "सुबह", "savere"),
    "afternoon": ("afternoon", "dopahar", "दोपहर"),
    "evening": ("evening", "shaam", "sham", "शाम"),
    "night": ("night", "raat", "रात"),
}
PREFERENCES = {
    "cheap": ("sasta", "saste", "sasti", "सस्ता", "सस्ती", "cheap", "cheapest", "budget", "kam daam"),
    "fast": ("jaldi", "जल्दी", "fast", "fastest", "quick", "direct"),
    "comfort": ("aaram", "आराम", "comfortable", "elder", "senior", "buzurg"),
}
_WEEKDAYS = {
    "monday": 0, "somvar": 0, "सोमवार": 0, "tuesday": 1, "mangalvar": 1, "मंगलवार": 1,
    "wednesday": 2, "budhvar": 2, "बुधवार": 2, "thursday": 3, "guruvar": 3, "गुरुवार": 3,
    "friday": 4, "shukravar": 4, "शुक्रवार": 4, "saturday": 5, "shanivar": 5, "शनिवार": 5,
    "sunday": 6, "ravivar": 6, "रविवार": 6,
}
_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


@dataclass
class NLUResult:
    intent: str
    confidence: float
    slots: dict[str, Any] = field(default_factory=dict)
    language: str = "en"
    matched: list[str] = field(default_factory=list)
    flags: dict[str, bool] = field(default_factory=dict)


def detect_language(text: str) -> str:
    if re.search(r"[ऀ-ॿ]", text):
        return "hi"
    tokens = set(normalize(text).split())
    hinglish_markers = {
        "kya", "kyun", "kyu", "aaya", "aya", "chahiye", "mera", "meri", "mere", "hai", "nahi", "nahin",
        "shaam", "sasta", "jaldi", "dukaan", "kab", "kitna", "se", "ka", "ki", "ke", "karo", "kar",
        "aaj", "kal", "paisa", "gaya", "abhi", "mujhe", "batao", "bhai", "ji", "aur", "wala",
    }
    return "hinglish" if tokens & hinglish_markers else "en"


def _parse_date(norm: str, today: datetime.date) -> str | None:
    iso = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", norm)
    if iso:
        try:
            return datetime.date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3))).isoformat()
        except ValueError:
            return None
    if any(_has(norm, w) for w in ("day after tomorrow", "parso", "parson", "परसों")):
        return (today + datetime.timedelta(days=2)).isoformat()
    if any(_has(norm, w) for w in ("tomorrow", "kal", "कल")):
        return (today + datetime.timedelta(days=1)).isoformat()
    if any(_has(norm, w) for w in ("today", "aaj", "आज", "tonight")):
        return today.isoformat()
    m = re.search(r"\b(\d{1,2})\s*(?:st|nd|rd|th)?\s+([a-z]{3})[a-z]*\b", norm)
    if m and m.group(2) in _MONTHS:
        day, month = int(m.group(1)), _MONTHS[m.group(2)]
        year = today.year
        try:
            d = datetime.date(year, month, day)
            if d < today:
                d = datetime.date(year + 1, month, day)
            return d.isoformat()
        except ValueError:
            return None
    for word, wd in _WEEKDAYS.items():
        if _has(norm, word):
            delta = (wd - today.weekday()) % 7 or 7
            return (today + datetime.timedelta(days=delta)).isoformat()
    return None


def _find_cities(norm: str) -> list[tuple[int, str, str]]:
    """Return [(position, matched_word, IATA)] in text order."""
    found: list[tuple[int, str, str]] = []
    padded = f" {norm} "
    for name, code in sorted(CITY_TO_IATA.items(), key=lambda kv: -len(kv[0])):
        for m in re.finditer(rf"(?= {re.escape(name)} )", padded):
            idx = m.start()
            if not any(abs(p - idx) < len(n) + 1 for p, n, _ in found):
                found.append((idx, name, code))
    for code in IATA_CODES:  # explicit IATA like "DEL to BOM"
        for m in re.finditer(rf"(?<!\w){code.lower()}(?!\w)", norm):
            if not any(abs(p - m.start()) < 3 for p, _, _ in found):
                found.append((m.start(), code.lower(), code))
    return sorted(found)


def extract_travel_slots(text: str, today: datetime.date | None = None) -> dict[str, Any]:
    today = today or datetime.date.today()
    norm = normalize(text)
    slots: dict[str, Any] = {}
    cities = _find_cities(norm)
    origin = destination = None
    for pos, name, code in cities:
        after = f" {norm} "[pos + len(name) + 1:].split()
        before = f" {norm} "[:pos].split()
        nxt = after[0] if after else ""
        prv = before[-1] if before else ""
        if nxt in ("se", "से", "sey") or prv == "from":
            origin = origin or code
        elif nxt in ("tak", "तक", "ko", "को", "jana", "jaana", "जाना") or prv in ("to", "for"):
            destination = destination or code
    remaining = [c for _, _, c in cities if c not in (origin, destination)]
    if origin is None and destination is None and len(remaining) >= 2:
        origin, destination = remaining[0], remaining[1]
    elif origin and destination is None and remaining:
        destination = remaining[0]
    elif destination and origin is None and remaining:
        origin = remaining[0]
    elif origin is None and destination is None and len(remaining) == 1:
        destination = remaining[0]
    if origin:
        slots["origin"] = origin
    if destination and destination != origin:
        slots["destination"] = destination
    date = _parse_date(norm, today)
    if date:
        slots["date"] = date
    for window, words in WINDOWS.items():
        if any(_has(norm, w) for w in words):
            slots["window"] = window
            break
    prefs = [p for p, words in PREFERENCES.items() if any(_has(norm, w) for w in words)]
    if prefs:
        slots["preference"] = "balanced" if {"cheap", "fast"} <= set(prefs) else prefs[0]
    ref = re.search(r"\bbk-?[a-z]*-?\d{3,}\b", norm)
    if ref:
        slots["booking_ref"] = ref.group(0).upper()
    return slots


def extract_loan_slots(text: str) -> dict[str, Any]:
    norm = normalize(text)
    slots: dict[str, Any] = {}
    m = re.search(r"(\d+(?:\.\d+)?)\s*(lakh|lac|लाख)", norm)
    if m:
        slots["amount"] = float(m.group(1)) * 100_000
    else:
        m = re.search(r"(\d+(?:\.\d+)?)\s*(hazaar|hazar|hajar|हजार|thousand|k)\b", norm)
        if m:
            slots["amount"] = float(m.group(1)) * 1000
        else:
            m = re.search(r"(?:₹|rs\.?\s*|inr\s*)?(\d{1,3}(?:,\d{2,3})+|\d{4,8})", norm)
            if m:
                slots["amount"] = float(m.group(1).replace(",", ""))
    t = re.search(r"(\d{1,2})\s*(mahine|mahina|month|months|महीने|महीना)", norm)
    if t:
        slots["tenure_months"] = int(t.group(1))
    else:
        y = re.search(r"(\d)\s*(saal|year|years|साल)", norm)
        if y:
            slots["tenure_months"] = int(y.group(1)) * 12
    return slots


def classify(text: str) -> NLUResult:
    """Tier 0 classifier. Returns intent 'unknown' with low confidence when unsure."""
    norm = normalize(text)
    language = detect_language(text)
    tokens = norm.split()

    def result(intent: str, conf: float, matched: list[str], **flags: bool) -> NLUResult:
        slots: dict[str, Any] = {}
        if intent in ("travel_flight_request", "travel_status"):
            slots = extract_travel_slots(text)
        elif intent in ("loan_emi_query", "loan_apply"):
            slots = extract_loan_slots(text)
        return NLUResult(intent, conf, slots, language, matched, dict(flags))

    # 1. Safety-critical patterns first (R3)
    for p in PAYMENT_REQUEST_PHRASES:
        if _has(norm, p):
            return result("payment_request", 0.95, [p])
    for p in LOAN_APPROVE_PHRASES:
        if _has(norm, p):
            return result("loan_approve_request", 0.95, [p])

    # 2. Explicit decline beats loan words ("nahi chahiye loan")
    for p in DECLINE_PHRASES:
        if _has(norm, p):
            return result("decline_offer", 0.95, [p])

    # 3. Scored lexicon
    scores: dict[str, float] = {}
    matched: dict[str, list[str]] = {}
    for intent, words in LEXICON.items():
        for phrase, weight in words.items():
            if _has(norm, phrase):
                scores[intent] = scores.get(intent, 0.0) + weight
                matched.setdefault(intent, []).append(phrase)
    fuzzy_used = False
    if not scores:
        for tok in tokens:
            if len(tok) < 5 or not tok.isascii():
                continue
            close = difflib.get_close_matches(tok, _FUZZY_KEYWORDS.keys(), n=1, cutoff=0.8)
            if close:
                intent = _FUZZY_KEYWORDS[close[0]]
                scores[intent] = scores.get(intent, 0.0) + 0.8
                matched.setdefault(intent, []).append(f"~{close[0]}")
                fuzzy_used = True

    # Travel: two known cities strongly imply a flight request
    if len(_find_cities(norm)) >= 2 and "travel_status" not in scores:
        scores["travel_flight_request"] = scores.get("travel_flight_request", 0.0) + 1.0
    if re.search(r"\bbk-?[a-z]*-?\d{3,}\b", norm):
        scores["travel_status"] = scores.get("travel_status", 0.0) + 1.5

    if not scores and len(_find_cities(norm)) == 1 and len(tokens) <= 4:
        return result("travel_flight_request", 0.76, ["single_city"])
    if not scores:
        if norm in BARE_NEGATIONS:
            return result("decline_offer", 0.5, [norm], bare_negation=True)
        return result("unknown", 0.0, [])

    # Specific beats generic: refund + payment_failed -> payment_failed covers both scopes.
    if "loan_emi_query" in scores and any(_has(norm, p) for p in LOAN_APPLY_PHRASES):
        return result("loan_apply", 0.9, matched["loan_emi_query"])
    if "refund_status" in scores and any(_has(norm, p) for p in REFUND_DEMAND_PHRASES):
        return result("refund_status", 0.9, matched["refund_status"], refund_demand=True)
    if scores.get("greeting") and len(scores) > 1:
        scores.pop("greeting")

    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    best, best_score = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    if fuzzy_used:
        conf = 0.78
    elif best_score >= 1.0:
        conf = 0.92 if best_score - second >= 0.4 else 0.8
    else:
        conf = 0.7 if best_score - second >= 0.3 else 0.6
    flags = {}
    if best == "refund_status" and any(_has(norm, p) for p in REFUND_DEMAND_PHRASES):
        flags["refund_demand"] = True
    return result(best, conf, matched.get(best, []), **flags)
