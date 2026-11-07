from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from missav_api import Client

from app.providers.hls import resolve_hls_quality
from app.schemas import FilterField, FilterOption, MediaItem

logger = logging.getLogger("xfreehd.web.providers.missav")


def _format_length(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if ":" in text:
        return text
    try:
        total = int(float(text))
    except ValueError:
        return text
    if total <= 0:
        return None
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _to_item(video: Any) -> MediaItem:
    m3u8 = getattr(video, "m3u8_base_url", None)
    keywords = getattr(video, "keywords", None) or []
    if isinstance(keywords, str):
        tags = [k.strip() for k in keywords.split(",") if k.strip()]
    else:
        tags = [str(k).strip() for k in keywords if str(k).strip()]

    url = getattr(video, "url", None) or ""
    video_id = url.rstrip("/").split("/")[-1] if url else None

    return MediaItem(
        provider="missav",
        url=url,
        id=video_id,
        title=getattr(video, "title", None),
        thumbnail=getattr(video, "thumbnail", None),
        length=_format_length(getattr(video, "length", None)),
        views=None,
        rating=None,
        author=None,
        publish_date=getattr(video, "publish_date", None),
        tags=tags,
        categories=[],
        stream_urls=[m3u8] if m3u8 else [],
        embed_url=None,
        is_private=None,
        extras={"stream_type": "hls"} if m3u8 else {},
    )


class MissAVProvider:
    """Provider wrapping https://github.com/EchterAlsFake/unofficial-api-for-missav"""

    id = "missav"
    name = "MissAV"
    description = "Unofficial async scraper for missav.ws (HLS / m3u8)"

    def __init__(self) -> None:
        self._client: Client | None = None

    @property
    def capabilities(self) -> list[str]:
        return ["search", "detail", "resolve_stream"]

    def filters(self) -> list[FilterField]:
        return [
            FilterField(
                key="video_count",
                label="Aantal",
                type="select",
                default="24",
                options=[
                    FilterOption(value="12", label="12"),
                    FilterOption(value="24", label="24"),
                    FilterOption(value="36", label="36"),
                    FilterOption(value="50", label="50"),
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
            raise RuntimeError("MissAVProvider is not started")
        return self._client

    async def search(
        self,
        query: str,
        *,
        filters: dict[str, Any] | None = None,
    ) -> AsyncIterator[MediaItem]:
        f = filters or {}
        try:
            video_count = int(f.get("video_count", 24))
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid video_count") from exc
        video_count = max(1, min(video_count, 50))

        seen: set[str] = set()
        async for result in self.client.search(query=query, video_count=video_count):
            video = getattr(result, "item", None)
            if video is None:
                continue
            item = _to_item(video)
            key = item.url or item.id
            if not key or key in seen:
                continue
            seen.add(key)
            yield item

    async def get_media(self, url: str) -> MediaItem:
        video = await self.client.get_video(url, load_html=True)
        return _to_item(video)

    async def resolve_stream(self, url: str, *, quality: str = "best") -> tuple[str, str | None]:
        video = await self.client.get_video(url, load_html=True)
        await video.load_fields("m3u8_base_url", "title")
        master = video.m3u8_base_url
        if not master:
            raise ValueError(f"No m3u8 URL for {url}")
        stream = await resolve_hls_quality(
            master,
            quality=quality or "best",
            headers=self.playback_headers(master),
            core=self.client.core,
        )
        return stream, video.title

    def playback_headers(self, stream_url: str | None = None) -> dict[str, str]:
        # surrit.com returns 403 without a missav Referer + browser UA
        _ = stream_url
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Referer": "https://missav.ws/",
            "Origin": "https://missav.ws",
            "Accept": "*/*",
        }
