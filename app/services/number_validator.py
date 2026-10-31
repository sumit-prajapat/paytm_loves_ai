"""Rule R1: every number in an outgoing reply must come from that turn's tool results.

The validator compares numbers in the reply against numbers in the deterministic tool facts
ONLY (never against the reply itself). A reply number is grounded when it equals a fact, or
is that fact rounded to an integer / one decimal (e.g. EMI 4489.36 shown as 4,489).
"""
from __future__ import annotations

import re
from typing import Any

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_NUMBER_RE = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\w])|\d+(?:\.\d+)?")


def _normalise(text: str) -> str:
    text = text.translate(_DEVANAGARI_DIGITS)
    # Remove digit-group commas (Indian and western): 1,00,000 -> 100000
    return re.sub(r"(?<=\d),(?=\d)", "", text)


def extract_numbers_from_text(text: str) -> set[float]:
    numbers: set[float] = set()
    for m in re.findall(r"\d+(?:\.\d+)?", _normalise(text)):
        try:
            numbers.add(float(m))
        except ValueError:
            continue
    return numbers


def extract_numbers_from_payload(payload: Any) -> set[float]:
    """Recursively collect numbers from tool outputs (dict/list/str/number)."""
    numbers: set[float] = set()
    if isinstance(payload, bool) or payload is None:
        return numbers
    if isinstance(payload, (int, float)):
        numbers.add(float(payload))
    elif isinstance(payload, dict):
        for v in payload.values():
            numbers |= extract_numbers_from_payload(v)
    elif isinstance(payload, (list, tuple, set)):
        for item in payload:
            numbers |= extract_numbers_from_payload(item)
    elif isinstance(payload, str):
        numbers |= extract_numbers_from_text(payload)
    return numbers


def _grounded(num: float, facts: set[float]) -> bool:
    for f in facts:
        if abs(num - f) < 1e-6:
            return True
        if abs(num - round(f)) < 1e-6 and num == int(num):
            return True  # fact rounded to integer for display
        if abs(num - round(f, 1)) < 1e-6:
            return True
    return False


class NumberValidator:
    @staticmethod
    def validate(
        response_text: str,
        tool_facts: Any,
        allowed_constants: set[float] | None = None,
    ) -> tuple[bool, set[float]]:
        """Return (is_valid, unauthorized_numbers). tool_facts must NOT contain the reply."""
        response_numbers = extract_numbers_from_text(response_text)
        facts = extract_numbers_from_payload(tool_facts) | set(allowed_constants or set())
        unauthorized = {n for n in response_numbers if not _grounded(n, facts)}
        return (not unauthorized), unauthorized


number_validator = NumberValidator()
