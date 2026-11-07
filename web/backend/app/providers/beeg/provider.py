from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from beeg_api import Client, extract_key

from app.providers.beeg.search import looks_like_video_id, search_videos
from app.providers.hls import resolve_hls_quality
from app.schemas import FilterField, FilterOption, MediaItem

logger = logging.getLogger("xfreehd.web.providers.beeg")


def _format_duration(seconds: Any) -> str | None:
    if seconds is None:
        return None
    try:
        total = int(seconds)
    except (TypeError, ValueError):
        return str(seconds)
    if total <= 0:
        return None
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _normalize_url(query: str) -> str:
    raw = query.strip()
    if not raw:
        raise ValueError("Plak een Beeg video-URL of numerieke ID")
    key = extract_key(raw)
    return f"https://beeg.com/{key}"


def _to_item(video: Any) -> MediaItem:
    m3u8 = getattr(video, "m3u8_base_url", None)
    tags = list(getattr(video, "tags", None) or [])
    video_id = getattr(video, "video_id", None) or getattr(video, "key", None)
    return MediaItem(
        provider="beeg",
        url=getattr(video, "url", None) or "",
        id=str(video_id) if video_id is not None else None,
        title=getattr(video, "title", None),
        thumbnail=getattr(video, "thumbnail", None),
        length=_format_duration(getattr(video, "duration", None)),
        views=None,
        rating=None,
        author=getattr(video, "author", None),
        publish_date=getattr(video, "publish_date", None),
        tags=tags,
        categories=[],
        stream_urls=[m3u8] if m3u8 else [],
        embed_url=None,
        is_private=None,
        extras={"stream_type": "hls"} if m3u8 else {},
    )


def _listing_to_item(row: dict[str, Any]) -> MediaItem:
    matched = row.get("matched_tag")
    extras: dict[str, Any] = {}
    if matched:
        extras["matched_tag"] = matched
    return MediaItem(
        provider="beeg",
        url=row.get("url") or "",
        id=str(row.get("video_id") or "") or None,
        title=row.get("title"),
        thumbnail=row.get("thumbnail"),
        length=_format_duration(row.get("duration")),
        views=None,
        rating=None,
        author=None,
        publish_date=None,
        tags=list(row.get("tags") or []),
        categories=[matched] if matched else [],
        stream_urls=[],
        embed_url=None,
        is_private=None,
        extras=extras,
    )


class BeegProvider:
    """Beeg provider: keyword search via externulls WS + URL/ID lookup via beeg_api."""

    id = "beeg"
    name = "Beeg"
    description = "Zoek tags/studios (externulls) of plak een video-URL/ID"

    def __init__(self) -> None:
        self._client: Client | None = None

    @property
    def capabilities(self) -> list[str]:
        return ["search", "detail", "resolve_stream"]

    def filters(self) -> list[FilterField]:
        return [
            FilterField(
                key="count",
                label="Max resultaten",
                type="select",
                default="24",
                options=[
                    FilterOption(value="12", label="12"),
                    FilterOption(value="24", label="24"),
                    FilterOption(value="48", label="48"),
                    FilterOption(value="100", label="100"),
                ],
            ),
        ]

    async def startup(self) -> None:
        self._client = Client()

    async def shutdown(self) -> None:
        if self._client is not None:
            await self._client.core.close()
            self._client = None

    @property
    def client(self) -> Client:
        if self._client is None:
            raise RuntimeError("BeegProvider is not started")
        return self._client

    async def search(
        self,
        query: str,
        *,
        filters: dict[str, Any] | None = None,
    ) -> AsyncIterator[MediaItem]:
        f = filters or {}
        try:
            count = int(f.get("count", 24))
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid count") from exc
        count = max(1, min(count, 100))

        raw = (query or "").strip()
        if not raw:
            return

        # Direct video URL / numeric ID → single result via official client
        if looks_like_video_id(raw):
            try:
                video = await self.client.get_video(_normalize_url(raw), load_api=True)
                yield _to_item(video)
                return
            except Exception:
                # Fall through to keyword search if ID parse fails oddly
                logger.info("Beeg ID lookup failed for %r; trying keyword search", raw)

        tag, videos = await search_videos(raw, max_count=count)
        if tag:
            logger.info(
                "Beeg search matched tag %s (%s) — %s videos",
                tag.get("name"),
                tag.get("slug"),
                len(videos),
            )
        for row in videos:
            yield _listing_to_item(row)

    async def get_media(self, url: str) -> MediaItem:
        video = await self.client.get_video(_normalize_url(url), load_api=True)
        return _to_item(video)

    async def resolve_stream(self, url: str, *, quality: str = "best") -> tuple[str, str | None]:
        video = await self.client.get_video(_normalize_url(url), load_api=True)
        await video.load_fields("m3u8_base_url", "title")
        master = video.m3u8_base_url
        if not master:
            raise ValueError(f"No m3u8 URL for {url}")
        stream = await resolve_hls_quality(
            master,
            quality=quality or "best",
            core=self.client.core,
        )
        return stream, video.title

    def playback_headers(self, stream_url: str | None = None) -> dict[str, str]:
        _ = stream_url
        return {}
