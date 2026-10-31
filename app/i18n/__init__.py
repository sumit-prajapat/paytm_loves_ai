"""Per-language reply templates (Tier 0: no LLM).

Templates live in app/i18n/locales/<lang>.json. To add a language (e.g. Marathi, Tamil, Bengali)
drop a new JSON file with the same keys; no code changes are needed. Missing keys fall back
along LANGUAGE_FALLBACKS, then to English.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

LOCALES_DIR = Path(__file__).parent / "locales"
DEFAULT_LANGUAGE = "en"
LANGUAGE_FALLBACKS: dict[str, list[str]] = {
    "mr": ["hi"],
    "gu": ["hi"],
    "hi": [],
    "hinglish": ["hi"],
}


@lru_cache
def _load(lang: str) -> dict[str, str]:
    path = LOCALES_DIR / f"{lang}.json"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def available_languages() -> list[str]:
    return sorted(p.stem for p in LOCALES_DIR.glob("*.json"))


def resolve_language(lang: str | None) -> str:
    """Map a requested language to one we have templates for."""
    if not lang:
        return "hi"
    lang = lang.lower()
    if _load(lang):
        return lang
    for fb in LANGUAGE_FALLBACKS.get(lang, []):
        if _load(fb):
            return fb
    return DEFAULT_LANGUAGE


def t(key: str, lang: str, **values: Any) -> str:
    """Render template `key` in `lang` with tool-provided values."""
    chain = [lang, *LANGUAGE_FALLBACKS.get(lang, []), DEFAULT_LANGUAGE]
    for candidate in chain:
        template = _load(candidate).get(key)
        if template is not None:
            try:
                return template.format(**values)
            except KeyError as exc:  # template/caller mismatch is a bug: surface it
                logger.error("Template %s/%s missing value %s", candidate, key, exc)
                raise
    raise KeyError(f"Unknown template key '{key}'")
