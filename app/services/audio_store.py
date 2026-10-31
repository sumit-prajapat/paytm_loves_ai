"""Generated reply audio served through short-lived HMAC-signed URLs (no auth header needed
for <audio> tags, but links expire and cannot be guessed)."""
from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from pathlib import Path

from app.config import get_settings

_EXT = {"audio/mpeg": "mp3", "audio/wav": "wav"}


def _sign(audio_id: str, exp: int) -> str:
    key = get_settings().JWT_SECRET_KEY.encode("utf-8")
    return hmac.new(key, f"{audio_id}:{exp}".encode(), hashlib.sha256).hexdigest()[:32]


def save_audio(data: bytes, content_type: str) -> dict:
    s = get_settings()
    ext = _EXT.get(content_type, "bin")
    audio_id = uuid.uuid4().hex
    folder = Path(s.AUDIO_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{audio_id}.{ext}").write_bytes(data)
    exp = int(time.time()) + s.AUDIO_URL_TTL_SECONDS
    base = s.PUBLIC_BASE_URL.rstrip("/")
    return {
        "audio_id": audio_id,
        "audio_url": f"{base}/api/v1/audio/{audio_id}?exp={exp}&sig={_sign(audio_id, exp)}",
        "content_type": content_type,
        "expires_at": exp,
        "bytes": len(data),
    }


def resolve_audio(audio_id: str, exp: int, sig: str) -> tuple[Path, str] | None:
    if not audio_id.isalnum() or exp < int(time.time()):
        return None
    if not hmac.compare_digest(sig, _sign(audio_id, exp)):
        return None
    folder = Path(get_settings().AUDIO_DIR)
    for ext, ctype in (("mp3", "audio/mpeg"), ("wav", "audio/wav")):
        path = folder / f"{audio_id}.{ext}"
        if path.exists():
            return path, ctype
    return None
