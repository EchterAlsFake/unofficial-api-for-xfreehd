from __future__ import annotations

import logging
import re
from urllib.parse import quote, urljoin, urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response

logger = logging.getLogger("xfreehd.web.proxy")
router = APIRouter(tags=["proxy"])

_URI_ATTR = re.compile(r'URI="([^"]+)"')


def _proxy_link(request: Request, target: str, provider: str | None) -> str:
    base = str(request.base_url).rstrip("/")
    q = f"url={quote(target, safe='')}&provider={quote(provider or '', safe='')}"
    return f"{base}/api/proxy?{q}"


def _rewrite_m3u8(body: str, playlist_url: str, request: Request, provider: str | None) -> str:
    out: list[str] = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            out.append(raw)
            continue
        if line.startswith("#"):
            def repl(match: re.Match[str]) -> str:
                abs_url = urljoin(playlist_url, match.group(1))
                return f'URI="{_proxy_link(request, abs_url, provider)}"'

            out.append(_URI_ATTR.sub(repl, raw))
            continue

        abs_url = urljoin(playlist_url, line)
        out.append(_proxy_link(request, abs_url, provider))
    return "\n".join(out) + "\n"


@router.get("/api/proxy")
async def proxy_media(
    request: Request,
    url: str = Query(..., min_length=8),
    provider: str | None = Query(None),
):
    """Proxy a CDN URL while attaching provider playback headers (for VLC/mpv)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(400, "Invalid url")

    media_provider = request.app.state.providers.get(provider)
    headers: dict[str, str] = {}
    getter = getattr(media_provider, "playback_headers", None)
    if callable(getter):
        headers = dict(getter(url) or {})

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=90.0) as client:
            upstream = await client.get(url, headers=headers)
    except Exception as exc:
        logger.exception("Proxy fetch failed for %s", url)
        raise HTTPException(502, f"Upstream fetch failed: {exc}") from exc

    if upstream.status_code >= 400:
        raise HTTPException(upstream.status_code, f"Upstream returned {upstream.status_code}")

    content_type = upstream.headers.get("content-type", "application/octet-stream")
    raw = upstream.content
    head = raw[:64].lstrip().decode("utf-8", "ignore")
    is_playlist = (
        "mpegurl" in content_type
        or "m3u8" in content_type
        or url.rstrip("/").split("?")[0].endswith(".m3u8")
        or head.startswith("#EXTM3U")
    )

    if is_playlist:
        rewritten = _rewrite_m3u8(raw.decode("utf-8", "replace"), url, request, provider)
        return Response(
            content=rewritten,
            media_type="application/vnd.apple.mpegurl",
            headers={"Cache-Control": "no-store"},
        )

    return Response(
        content=raw,
        media_type=content_type,
        headers={"Cache-Control": "no-store"},
    )
