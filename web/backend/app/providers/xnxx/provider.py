from __future__ import annotations

import logging
import re
from typing import Any, AsyncIterator

from xnxx_api import Client

from app.providers.hls import resolve_hls_quality
from app.schemas import FilterField, FilterOption, MediaItem

logger = logging.getLogger("xfreehd.web.providers.xnxx")

_ISO_DUR = re.compile(
    r"^PT(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+)S)?$",
    re.IGNORECASE,
)


def _format_length(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if ":" in text and not text.upper().startswith("PT"):
        return text
    match = _ISO_DUR.match(text)
    if match:
        h = int(match.group("h") or 0)
        m = int(match.group("m") or 0)
        s = int(match.group("s") or 0)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"
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
    tags = getattr(video, "tags", None) or []
    if isinstance(tags, str):
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    else:
        tag_list = [str(t).strip() for t in tags if str(t).strip()]

    return MediaItem(
        provider="xnxx",
        url=getattr(video, "url", None) or "",
        id=getattr(video, "video_id", None) or getattr(video, "video_eid", None),
        title=getattr(video, "title", None),
        thumbnail=getattr(video, "thumbnail", None),
        length=_format_length(getattr(video, "length", None)),
        views=str(getattr(video, "views", None)) if getattr(video, "views", None) is not None else None,
        rating=getattr(video, "rating", None),
        author=getattr(video, "author", None),
        publish_date=getattr(video, "publish_date", None),
        tags=tag_list,
        categories=[],
        stream_urls=[m3u8] if m3u8 else [],
        embed_url=None,
        is_private=None,
        extras={"stream_type": "hls", "max_quality": getattr(video, "max_quality", None)}
        if m3u8
        else {"max_quality": getattr(video, "max_quality", None)},
    )


class XNXXProvider:
    """Provider wrapping https://github.com/EchterAlsFake/unofficial-api-for-xnxx"""

    id = "xnxx"
    name = "XNXX"
    description = "Unofficial async scraper for xnxx.com (HLS / m3u8)"

    def __init__(self) -> None:
        self._client: Client | None = None

    @property
    def capabilities(self) -> list[str]:
        return ["search", "detail", "resolve_stream"]

    def filters(self) -> list[FilterField]:
        return [
            FilterField(
                key="pages",
                label="Pagina’s",
                type="number",
                default=1,
                min=1,
                max=5,
            ),
            FilterField(
                key="mode",
                label="Modus",
                type="select",
                default="",
                options=[
                    FilterOption(value="", label="Standaard"),
                    FilterOption(value="/hits", label="Hits"),
                    FilterOption(value="/random", label="Random"),
                ],
            ),
            FilterField(
                key="upload_time",
                label="Upload",
                type="select",
                default="",
                options=[
                    FilterOption(value="", label="Alle tijd"),
                    FilterOption(value="/month", label="Maand"),
                    FilterOption(value="/year", label="Jaar"),
                ],
            ),
            FilterField(
                key="length",
                label="Duur",
                type="select",
                default="",
                options=[
                    FilterOption(value="", label="Alle"),
                    FilterOption(value="/0-10min", label="0–10 min"),
                    FilterOption(value="/10-20min", label="10–20 min"),
                    FilterOption(value="/10min+", label="10+ min"),
                    FilterOption(value="/20min+", label="20+ min"),
                ],
            ),
            FilterField(
                key="searching_quality",
                label="Kwaliteit",
                type="select",
                default="",
                options=[
                    FilterOption(value="", label="Alle"),
                    FilterOption(value="/hd-only", label="720p+"),
                    FilterOption(value="/fullhd", label="1080p+"),
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
            raise RuntimeError("XNXXProvider is not started")
        return self._client

    async def search(
        self,
        query: str,
        *,
        filters: dict[str, Any] | None = None,
    ) -> AsyncIterator[MediaItem]:
        f = filters or {}
        try:
            pages = int(f.get("pages", 1))
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid pages") from exc
        pages = max(1, min(pages, 5))

        mode = str(f.get("mode", "") or "")
        upload_time = str(f.get("upload_time", "") or "")
        length = str(f.get("length", "") or "")
        quality = str(f.get("searching_quality", "") or "")

        allowed_mode = {"", "/hits", "/random"}
        allowed_time = {"", "/year", "/month"}
        allowed_length = {"", "/0-10min", "/10min+", "/10-20min", "/20min+"}
        allowed_quality = {"", "/hd-only", "/fullhd"}
        if mode not in allowed_mode:
            raise ValueError(f"Invalid mode '{mode}'")
        if upload_time not in allowed_time:
            raise ValueError(f"Invalid upload_time '{upload_time}'")
        if length not in allowed_length:
            raise ValueError(f"Invalid length '{length}'")
        if quality not in allowed_quality:
            raise ValueError(f"Invalid searching_quality '{quality}'")

        seen: set[str] = set()
        async for result in self.client.search_videos(
            query=query,
            pages=pages,
            mode=mode,
            upload_time=upload_time,
            length=length,
            searching_quality=quality,
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
        await video.load_fields("m3u8_base_url", "title")
        master = video.m3u8_base_url
        if not master:
            raise ValueError(f"No m3u8 URL for {url}")
        # Master playlists list 250p…1080p; VLC often sticks to the first/low rung.
        stream = await resolve_hls_quality(
            master,
            quality=quality or "best",
            core=self.client.core,
        )
        return stream, video.title

    def playback_headers(self, stream_url: str | None = None) -> dict[str, str]:
        _ = stream_url
        # xnxx-cdn currently serves without Referer; keep empty so M3U uses direct URLs
        return {}
