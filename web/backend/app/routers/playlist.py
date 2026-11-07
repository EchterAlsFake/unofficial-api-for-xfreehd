from __future__ import annotations

import logging
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.exporters.base import PlaylistEntry
from app.schemas import PlaylistRequest

logger = logging.getLogger("xfreehd.web.playlist")
router = APIRouter(tags=["playlist"])


def _needs_proxy(headers: dict[str, str], stream_url: str) -> bool:
    if not headers:
        return False
    host = stream_url.lower()
    return "surrit.com" in host or "m3u8" in host or bool(headers.get("Referer"))


@router.post("/api/playlist/export")
async def export_playlist(request: Request, body: PlaylistRequest) -> Response:
    if not body.items:
        raise HTTPException(400, "No playlist items provided")

    exporters = request.app.state.exporters
    providers = request.app.state.providers
    exporter = exporters.get(body.exporter)
    base = str(request.base_url).rstrip("/")

    entries: list[PlaylistEntry] = []
    for item in body.items:
        title = item.title or item.url
        provider_id = item.provider or body.provider
        media_provider = providers.get(provider_id)
        stream_url: str | None = None

        if body.resolve and "resolve_stream" in media_provider.capabilities:
            try:
                stream_url, resolved_title = await media_provider.resolve_stream(
                    item.url,
                    quality=body.quality,
                )
                title = resolved_title or title
            except Exception as exc:
                logger.warning("Skipping %s: %s", item.url, exc)
                continue
        else:
            stream_url = item.url

        if not stream_url:
            continue

        headers: dict[str, str] = {}
        getter = getattr(media_provider, "playback_headers", None)
        if callable(getter):
            try:
                headers = dict(getter(stream_url) or {})
            except Exception as exc:
                logger.warning("playback_headers failed for %s: %s", item.url, exc)

        play_url = stream_url
        play_headers = headers
        # Local proxy so VLC/mpv don't need CDN Referer headers themselves
        if _needs_proxy(headers, stream_url):
            play_url = (
                f"{base}/api/proxy?url={quote(stream_url, safe='')}"
                f"&provider={quote(media_provider.id, safe='')}"
            )
            play_headers = {}

        entries.append(PlaylistEntry(title=title, url=play_url, http_headers=play_headers))

    if not entries:
        raise HTTPException(502, "Could not resolve any stream URLs for the playlist")

    content = exporter.render(entries)
    filename = f"playlist.{exporter.extension}"
    return Response(
        content=content,
        media_type=exporter.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/api/playlist.m3u")
async def export_playlist_m3u_legacy(request: Request, body: PlaylistRequest) -> Response:
    body.exporter = "m3u"
    return await export_playlist(request, body)
