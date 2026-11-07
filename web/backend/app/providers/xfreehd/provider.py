from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from xfreehd_api import Client

from app.schemas import FilterField, FilterOption, MediaItem

logger = logging.getLogger("xfreehd.web.providers.xfreehd")

SORT_MAP = {
    "relevance": None,
    "most_recent": "mr",
    "most_viewed": "mv",
    "top_rated": "tr",
    "longest": "lg",
}

TIME_MAP = {
    "all": None,
    "today": "t",
    "week": "w",
    "month": "m",
    "year": "y",
}


def _pick_stream_url(cdn_urls: list[str], quality: str = "best") -> str | None:
    if not cdn_urls:
        return None
    q = (quality or "best").lower()
    if len(cdn_urls) == 1:
        return cdn_urls[0]
    if q in ("hd", "best", "720", "1080", "2160", "4k"):
        return cdn_urls[-1]
    if q in ("half", "mid", "middle"):
        return cdn_urls[len(cdn_urls) // 2]
    return cdn_urls[0]


def _to_item(video: Any) -> MediaItem:
    return MediaItem(
        provider="xfreehd",
        url=getattr(video, "url", None) or "",
        id=getattr(video, "video_id", None),
        title=getattr(video, "title", None),
        thumbnail=getattr(video, "thumbnail", None),
        length=getattr(video, "length", None),
        views=getattr(video, "views", None),
        rating=getattr(video, "rating", None),
        author=getattr(video, "author", None),
        publish_date=getattr(video, "publish_date", None),
        tags=list(getattr(video, "tags", None) or []),
        categories=list(getattr(video, "categories", None) or []),
        stream_urls=list(getattr(video, "cdn_urls", None) or []),
        embed_url=getattr(video, "embed_url", None),
        is_private=getattr(video, "is_private", None),
    )


class XFreeHDProvider:
    id = "xfreehd"
    name = "XFreeHD"
    description = "Unofficial async scraper for xfreehd.com"

    def __init__(self) -> None:
        self._client: Client | None = None

    @property
    def capabilities(self) -> list[str]:
        return ["search", "detail", "resolve_stream"]

    def filters(self) -> list[FilterField]:
        return [
            FilterField(
                key="sort_by",
                label="Sortering",
                type="select",
                default="relevance",
                options=[
                    FilterOption(value="relevance", label="Relevantie"),
                    FilterOption(value="most_recent", label="Nieuwste"),
                    FilterOption(value="most_viewed", label="Meest bekeken"),
                    FilterOption(value="top_rated", label="Best beoordeeld"),
                    FilterOption(value="longest", label="Langste"),
                ],
            ),
            FilterField(
                key="time_frame",
                label="Periode",
                type="select",
                default="all",
                options=[
                    FilterOption(value="all", label="Alle tijd"),
                    FilterOption(value="today", label="Vandaag"),
                    FilterOption(value="week", label="Week"),
                    FilterOption(value="month", label="Maand"),
                    FilterOption(value="year", label="Jaar"),
                ],
            ),
            FilterField(
                key="pages",
                label="Pagina’s",
                type="number",
                default=2,
                min=1,
                max=10,
            ),
        ]

    async def startup(self) -> None:
        self._client = Client()

    async def shutdown(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

    @property
    def client(self) -> Client:
        if self._client is None:
            raise RuntimeError("XFreeHDProvider is not started")
        return self._client

    async def search(
        self,
        query: str,
        *,
        filters: dict[str, Any] | None = None,
    ) -> AsyncIterator[MediaItem]:
        f = filters or {}
        sort_by = str(f.get("sort_by", "relevance"))
        time_frame = str(f.get("time_frame", "all"))
        pages = int(f.get("pages", 2))

        if sort_by not in SORT_MAP:
            raise ValueError(f"Invalid sort_by '{sort_by}'")
        if time_frame not in TIME_MAP:
            raise ValueError(f"Invalid time_frame '{time_frame}'")
        pages = max(1, min(pages, 10))

        seen: set[str] = set()
        async for result in self.client.search(
            query=query,
            pages=pages,
            sort_by=SORT_MAP[sort_by],
            time_frame=TIME_MAP[time_frame],
        ):
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
        await video.load_fields("cdn_urls", "title")
        stream = _pick_stream_url(list(video.cdn_urls or []), quality)
        if not stream:
            raise ValueError(f"No stream URL for {url}")
        return stream, video.title

    def playback_headers(self, stream_url: str | None = None) -> dict[str, str]:
        _ = stream_url
        return {}
