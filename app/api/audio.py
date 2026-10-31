"""Serve generated reply audio via short-lived signed URLs."""
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.services.audio_store import resolve_audio

router = APIRouter(prefix="/audio", tags=["Audio"])


@router.get("/{audio_id}")
async def get_audio(audio_id: str, exp: int = Query(...), sig: str = Query(..., max_length=64)):
    found = resolve_audio(audio_id, exp, sig)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Audio not found or link expired")
    path, ctype = found
    return FileResponse(path, media_type=ctype, headers={"Cache-Control": "private, max-age=300"})
