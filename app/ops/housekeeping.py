"""The ONLY scheduler in the app (R11): system housekeeping that touches no user data.

Allowed jobs: delete expired generated audio files, prune the in-process cache.
This module must never import DB models or open a DB session; a test enforces that, and
another test asserts the running scheduler only has jobs from HOUSEKEEPING_JOB_IDS.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.core.cache import cache

logger = logging.getLogger(__name__)

HOUSEKEEPING_JOB_IDS = frozenset({"expire_audio_files", "prune_memory_cache"})
scheduler = AsyncIOScheduler()


def expire_audio_files() -> int:
    """Delete generated reply audio older than its URL lifetime (files only, no user rows)."""
    s = get_settings()
    audio_dir = Path(s.AUDIO_DIR)
    if not audio_dir.exists():
        return 0
    cutoff = time.time() - s.AUDIO_URL_TTL_SECONDS
    removed = 0
    for f in audio_dir.glob("*.*"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        except OSError:
            logger.warning("Could not remove expired audio file %s", f.name)
    return removed


def prune_memory_cache() -> int:
    return cache.prune()


JOBS = {
    "expire_audio_files": (expire_audio_files, 600),
    "prune_memory_cache": (prune_memory_cache, 900),
}


def start_housekeeping() -> None:
    if not get_settings().HOUSEKEEPING_ENABLED or scheduler.running:
        return
    for job_id, (func, seconds) in JOBS.items():
        assert job_id in HOUSEKEEPING_JOB_IDS
        scheduler.add_job(func, "interval", seconds=seconds, id=job_id, replace_existing=True)
    scheduler.start()
    logger.info("Housekeeping scheduler started: %s", sorted(JOBS))


def stop_housekeeping() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
