import re
from typing import Any


def extract_numbers_from_text(text: str) -> set[float]:
    """Extracts all integer and floating point numbers from text strings,

    handling currency formats (e.g. ₹1,800, 1800, 1200.50, 12%).
    """
    # Remove commas from formatted numbers (e.g. 1,800 -> 1800)
    cleaned = re.sub(r"(?<=\d),(?=\d)", "", text)
    # Match numbers (integers or floats)
    matches = re.findall(r"\b\d+(?:\.\d+)?\b", cleaned)
    numbers = set()
    for m in matches:
        try:
            val = float(m)
            numbers.add(val)
        except ValueError:
            pass
    return numbers


def extract_numbers_from_payload(payload: Any) -> set[float]:
    """Recursively extracts all numbers from a structured dict or list payload."""
    numbers = set()
    if isinstance(payload, (int, float)) and not isinstance(payload, bool):
        numbers.add(float(payload))
    elif isinstance(payload, dict):
        for v in payload.values():
            numbers.update(extract_numbers_from_payload(v))
    elif isinstance(payload, (list, tuple, set)):
        for item in payload:
            numbers.update(extract_numbers_from_payload(item))
    elif isinstance(payload, str):
        # Extract potential numbers inside strings (e.g. "₹1,800")
        numbers.update(extract_numbers_from_text(payload))
    return numbers


class NumberValidator:
    """Enforces Non-Negotiable Rule R1: Rejects any LLM reply containing a number

    not present in the deterministic tool outputs of that turn.
    """

    @staticmethod
    def validate(response_text: str, tool_outputs: Any, allowed_constants: set[float] | None = None) -> tuple[bool, set[float]]:
        """Returns (is_valid, set_of_unauthorized_numbers).

        allowed_constants can include UI standards like 24, 48, 7 (standard SLA hours/days).
        """
        response_numbers = extract_numbers_from_text(response_text)
        tool_numbers = extract_numbers_from_payload(tool_outputs)

        # Standard SLAs permitted in customer communication
        standard_constants = {0.0, 1.0, 2.0, 3.0, 4.0, 7.0, 24.0, 48.0}
        if allowed_constants:
            standard_constants.update(allowed_constants)

        unauthorized = set()
        for num in response_numbers:
            # Check if num or close match exists in tool_numbers or standard_constants
            match_found = False
            for allowed in tool_numbers.union(standard_constants):
                if abs(num - allowed) < 1e-3:
                    match_found = True
                    break
            if not match_found:
                unauthorized.add(num)

        is_valid = len(unauthorized) == 0
        return is_valid, unauthorized


number_validator = NumberValidator()
