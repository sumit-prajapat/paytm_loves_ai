import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any
import bcrypt
import jwt
from app.config import get_settings

settings = get_settings()


class UserRole:
    MERCHANT = "merchant"
    TRAVELLER = "traveller"
    OPS_AGENT = "ops_agent"
    ADMIN = "admin"


# ---------------------------------------------------------------------------
# Password Hashing & Verification
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Hashes a password with bcrypt and returns a utf-8 string."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT Token Management
# ---------------------------------------------------------------------------
def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": now, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict[str, Any]) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "iat": now, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Tamper-Evident Audit Chain Hash
# ---------------------------------------------------------------------------
def compute_audit_hash(
    previous_hash: str,
    case_id: str,
    actor: str,
    action: str,
    detail: Any,
    ts: datetime,
) -> str:
    """Computes SHA-256 hash chaining previous row hash with current row data."""
    detail_str = json.dumps(detail, sort_keys=True, default=str) if detail else ""
    ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
    raw_payload = f"{previous_hash}|{case_id}|{actor}|{action}|{detail_str}|{ts_str}"
    return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# PII Masking
# ---------------------------------------------------------------------------
def mask_pii(text: str) -> str:
    """Redacts Indian phone numbers, Aadhaar, cards, and OTPs/PINs in logs and prompts."""
    # Mask 10-digit Indian phone numbers: e.g. 9876543210 -> 98******10
    text = re.sub(
        r"\b([6-9]\d{2})\d{5}(\d{2})\b",
        r"\1*****\2",
        text,
    )
    # Mask Aadhaar numbers: e.g. 1234 5678 9012 -> ****-****-9012
    text = re.sub(
        r"\b\d{4}[\s-]?\d{4}[\s-](\d{4})\b",
        r"****-****-\1",
        text,
    )
    # Mask credit/debit card numbers: e.g. 4111 2222 3333 4444 -> ****-****-****-4444
    text = re.sub(
        r"\b(?:\d{4}[ -]?){3}(\d{4})\b",
        r"****-****-****-\1",
        text,
    )
    # Mask PIN / OTP when adjacent to keywords
    text = re.sub(
        r"(?i)\b(pin|otp|password|cvv|secret)\s*(?:is|hai|=|:)?\s*(\d{4,6})\b",
        r"\1 [REDACTED_CREDENTIAL]",
        text,
    )
    return text


# ---------------------------------------------------------------------------
# Prompt Injection Detection
# ---------------------------------------------------------------------------
INJECTION_PATTERNS = [
    re.compile(r"(?i)\b(ignore|forget|override|bypass)\b.*\b(previous|system|instruction|rules|prompt)\b"),
    re.compile(r"(?i)\b(system\s*prompt|system\s*instruction|reveal\s*prompt|print\s*prompt)\b"),
    re.compile(r"(?i)\b(act\s*as\s*(admin|root|superuser|developer|dan|system))\b"),
    re.compile(r"(?i)\b(jailbreak|prompt\s*injection)\b"),
    re.compile(r"(?i)\b(show|dump|list|leak)\b.*\b(all\s*users|passwords|database|secrets|api\s*keys)\b"),
    re.compile(r"(?i)\b(drop\s*table|select\s*\*|union\s*select|insert\s*into)\b"),
]


def detect_prompt_injection(text: str) -> tuple[bool, str | None]:
    """Detects adversarial injection attacks aimed at manipulating system rules or extracting secrets."""
    for pattern in INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            return True, f"Suspicious injection pattern detected: '{match.group(0)}'"
    return False, None


# ---------------------------------------------------------------------------
# Output Leak Sanitization
# ---------------------------------------------------------------------------
LEAK_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z-_]{25,}"),  # Google API key
    re.compile(r"sk-[0-9A-Za-z-_]{20,}"),  # OpenAI key
    re.compile(r"gsk_[0-9A-Za-z-_]{20,}"),  # Groq key
    re.compile(r"Traceback \(most recent call last\):"),  # Stack trace
    re.compile(r"sqlite\+aiosqlite:///[^\s]+"),  # DB URL
    re.compile(r"postgresql://[^\s]+"),  # DB URL
]


def sanitize_agent_output(text: str) -> str:
    """Sanitizes outgoing agent text to prevent accidental leakage of API keys, stack traces, or credentials."""
    sanitized = text
    for pattern in LEAK_PATTERNS:
        sanitized = pattern.sub("[REDACTED_CONFIDENTIAL_DATA]", sanitized)
    return sanitized


# ---------------------------------------------------------------------------
# Code-Level Agent Tool Denylist (Rule R3)
# ---------------------------------------------------------------------------
DISALLOWED_AGENT_TOOLS = {
    "confirm_payment",
    "process_payment",
    "execute_charge",
    "approve_loan",
    "issue_refund",
    "send_refund",
    "execute_refund",
    "direct_debit",
}

AGENT_ALLOW_LISTS: dict[str, set[str]] = {
    "listener": {"classify_intent_and_extract_slots", "sanitize_security_input"},
    "context": {"fetch_context_bundle"},
    "diagnostician": {"diagnose_root_cause_and_consult_rag"},
    "guardian": {"evaluate_action_policy"},
    "action": {"execute_safe_action"},
    "offer": {"evaluate_consent_first_loan_offer"},
    "handoff": {"package_escalation_dossier"},
    "planner": {"generate_travel_roadmap"},
    "search": {"search_flight_inventories"},
    "ranker": {"rank_and_package_human_handoff"},
    "captain": {"finalize_response"},
}


def is_tool_allowed_for_agent(agent_name: str, tool_name: str) -> bool:
    """Enforces code-level tool allow-lists and global financial denylist (Rule R3)."""
    # 1. Deny any financial confirmation tool globally
    if tool_name in DISALLOWED_AGENT_TOOLS:
        return False

    # 2. Check agent specific allow-list
    allowed = AGENT_ALLOW_LISTS.get(agent_name, set())
    return tool_name in allowed
