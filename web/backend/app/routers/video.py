from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request

logger = logging.getLogger("xfreehd.web.video")
router = APIRouter(tags=["video"])


@router.get("/api/video")
async def get_video(
    request: Request,
    url: str = Query(..., min_length=1),
    provider: str | None = Query(None),
):
    media_provider = request.app.state.providers.get(provider)
    try:
        item = await media_provider.get_media(url)
    except Exception as exc:
        logger.exception("Failed to load media %s via %s", url, media_provider.id)
        raise HTTPException(502, f"Failed to load media: {exc}") from exc
    return item.model_dump()
