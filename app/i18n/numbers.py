"""Deterministic number formatting for replies and speech.

- format_inr: Indian digit grouping (1,00,000) for display text.
- money: API representation {amount_paise, formatted}.
- spoken_number: number words for Soundbox / TTS (Hindi in Devanagari, Hinglish in Roman).
"""
from __future__ import annotations

_ROMAN_0_99 = (
    "shunya ek do teen chaar paanch chhah saat aath nau das gyaarah baarah terah chaudah pandrah "
    "solah satrah athaarah unnees bees ikkees baaees teis chaubees pachchees chhabbees sattaais "
    "atthaais untees tees ikattees battees taintees chauntees paintees chhattees saintees adtees "
    "untaalees chaalees iktaalees bayaalees taintaalees chavaalees paintaalees chhiyaalees "
    "saintaalees adtaalees unchaas pachaas ikyaavan baavan tirpan chauvan pachpan chhappan "
    "sattaavan atthaavan unsath saath iksath baasath tirsath chausath painsath chhiyaasath sadsath "
    "adsath unhattar sattar ikhattar bahattar tihattar chauhattar pachhattar chhihattar sathattar "
    "athattar unaasi assi ikyaasi bayaasi tiraasi chauraasi pachaasi chhiyaasi sattaasi atthaasi "
    "navaasi nabbe ikyaanve baanve tiraanve chauraanve pachaanve chhiyaanve sattaanve atthaanve "
    "ninyaanve"
).split()

_DEVA_0_99 = (
    "शून्य एक दो तीन चार पाँच छह सात आठ नौ दस ग्यारह बारह तेरह चौदह पंद्रह सोलह सत्रह अठारह "
    "उन्नीस बीस इक्कीस बाईस तेईस चौबीस पच्चीस छब्बीस सत्ताईस अट्ठाईस उनतीस तीस इकतीस बत्तीस "
    "तैंतीस चौंतीस पैंतीस छत्तीस सैंतीस अड़तीस उनतालीस चालीस इकतालीस बयालीस तैंतालीस चवालीस "
    "पैंतालीस छियालीस सैंतालीस अड़तालीस उनचास पचास इक्यावन बावन तिरपन चौवन पचपन छप्पन सत्तावन "
    "अट्ठावन उनसठ साठ इकसठ बासठ तिरसठ चौंसठ पैंसठ छियासठ सड़सठ अड़सठ उनहत्तर सत्तर इकहत्तर "
    "बहत्तर तिहत्तर चौहत्तर पचहत्तर छिहत्तर सतहत्तर अठहत्तर उन्यासी अस्सी इक्यासी बयासी तिरासी "
    "चौरासी पचासी छियासी सत्तासी अट्ठासी नवासी नब्बे इक्यानवे बानवे तिरानवे चौरानवे पचानवे "
    "छियानवे सत्तानवे अट्ठानवे निन्यानवे"
).split()

assert len(_ROMAN_0_99) == 100 and len(_DEVA_0_99) == 100

_UNITS = {
    "roman": {"sau": "sau", "hazaar": "hazaar", "lakh": "lakh", "crore": "crore", "minus": "minus"},
    "deva": {"sau": "सौ", "hazaar": "हज़ार", "lakh": "लाख", "crore": "करोड़", "minus": "माइनस"},
}


def _words(n: int, script: str) -> str:
    table = _DEVA_0_99 if script == "deva" else _ROMAN_0_99
    u = _UNITS[script]
    if n < 100:
        return table[n]
    parts: list[str] = []
    for div, unit in ((10_000_000, "crore"), (100_000, "lakh"), (1000, "hazaar")):
        if n >= div:
            parts.append(f"{_words(n // div, script)} {u[unit]}")
            n %= div
    if n >= 100:
        parts.append(f"{table[n // 100]} {u['sau']}")
        n %= 100
    if n:
        parts.append(table[n])
    return " ".join(parts)


def spoken_number(value: float | int, language: str) -> str:
    """Number in words for speech. 1800 -> 'athaarah sau' (Hindi idiom for 1100..9900 in hundreds)."""
    n = int(round(value))
    if language == "en":
        return f"{n:,}".replace(",", " ")  # TTS reads plain digits fine in English
    script = "deva" if language == "hi" else "roman"
    if n < 0:
        return f"{_UNITS[script]['minus']} {spoken_number(-n, language)}"
    # Idiomatic hundreds: 1800 -> "athaarah sau" instead of "ek hazaar aath sau"
    if 1100 <= n <= 9900 and n % 100 == 0 and n % 1000 != 0:
        table = _DEVA_0_99 if script == "deva" else _ROMAN_0_99
        return f"{table[n // 100]} {_UNITS[script]['sau']}"
    return _words(n, script)


def format_indian_digits(value: float | int) -> str:
    """1800 -> '1,800'; 100000 -> '1,00,000'; 4489.36 -> '4,489.36'."""
    negative = value < 0
    value = abs(value)
    rounded = round(float(value), 2)
    if rounded == int(rounded):
        int_part, frac = str(int(rounded)), ""
    else:
        int_part, frac_digits = f"{rounded:.2f}".split(".")
        frac = "." + frac_digits
    if len(int_part) > 3:
        head, tail = int_part[:-3], int_part[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        int_part = ",".join(groups) + "," + tail
    return ("-" if negative else "") + int_part + frac


def format_inr(value: float | int) -> str:
    return f"₹{format_indian_digits(value)}"


def money(value: float | int | None) -> dict | None:
    """API money representation: integer paise plus a display string."""
    if value is None:
        return None
    return {"amount_paise": int(round(float(value) * 100)), "formatted": format_inr(value)}


def format_rate(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:g}"
