from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger("xfreehd.web.search")
router = APIRouter(tags=["search"])

_RESERVED = {"q", "provider", "stream", "pages", "sort_by", "time_frame"}


def _filters_from_request(
    request: Request,
    *,
    sort_by: str | None,
    time_frame: str | None,
    pages: int | None,
) -> dict[str, Any]:
    filters: dict[str, Any] = {}
    # Provider-specific filters arrive as extra query params from the UI
    for key, value in request.query_params.multi_items():
        if key in _RESERVED:
            continue
        filters[key] = value
    if sort_by is not None:
        filters["sort_by"] = sort_by
    if time_frame is not None:
        filters["time_frame"] = time_frame
    if pages is not None:
        filters["pages"] = pages
    return filters


@router.get("/api/search")
async def search(
    request: Request,
    q: str = Query(..., min_length=1),
    provider: str | None = Query(None),
    pages: int = Query(2, ge=1, le=10),
    sort_by: str = Query("relevance"),
    time_frame: str = Query("all"),
    stream: bool = Query(True),
):
    media_provider = request.app.state.providers.get(provider)
    filters = _filters_from_request(
        request,
        sort_by=sort_by,
        time_frame=time_frame,
        pages=pages,
    )

    if not stream:
        results = []
        try:
            async for item in media_provider.search(q, filters=filters):
                results.append(item.model_dump())
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return {"query": q, "provider": media_provider.id, "results": results}

    async def event_stream() -> AsyncIterator[str]:
        count = 0
        try:
            async for item in media_provider.search(q, filters=filters):
                count += 1
                payload = json.dumps(
                    {"type": "item", "data": item.model_dump()},
                    ensure_ascii=False,
                )
                yield f"data: {payload}\n\n"
            done = json.dumps(
                {"type": "done", "count": count, "provider": media_provider.id},
                ensure_ascii=False,
            )
            yield f"data: {done}\n\n"
        except ValueError as exc:
            err = json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False)
            yield f"data: {err}\n\n"
        except Exception as exc:
            logger.exception("Search failed for %r via %s", q, media_provider.id)
            err = json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False)
            yield f"data: {err}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
