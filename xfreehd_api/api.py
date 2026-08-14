"""
Copyright (C) 2025-2026 Johannes Habel
Licensed under LGPLv3

If you haven't received the license with this library, see: https://www.gnu.org/licenses/lgpl-3.0.en.html
Only use this library under your local laws. I do not endorse any copyright infringement.
"""
import math
import asyncio
import logging
import os.path

from typing import AsyncGenerator, ClassVar
from dataclasses import dataclass
from selectolax.lexbor import LexborHTMLParser
from base_api.modules.config import IteratorConfig
from base_api import (
    BaseCore,
    BaseMedia,
    DownloadConfigRAW,
    ErrorAction,
    ErrorMode,
    Helper,
    MediaLoadError,
    MediaLoadErrors,
    RetryPolicy,
    ScrapeErrorContext,
    ScrapeResult,
    media_field,
)
from base_api.modules.errors import (
    BotProtectionDetected,
    HTTPStatusError,
    InvalidProxy,
    NetworkRequestError,
    RequestRetriesExhausted,
    ResourceGone,
    UnknownError,
)

from xfreehd_api.modules.consts import REGEX_THUMBNAIL, REGEX_VIDEO_DURATION, extractor_search
from xfreehd_api.modules.errors import (NetworkError, NotFound, UnknownNetworkError, BotDetection, ProxyError,
                                        DownloadFailed)


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

SCRAPE_RETRY_POLICY = RetryPolicy(max_attempts=3)


def make_iterator_config() -> IteratorConfig:
    return IteratorConfig(
        load_specific_sources=("html",),
        item_retry=None,
        page_retry=None,
        page_error_mode=ErrorMode.SKIP,
        item_error_handler=None,
        page_error_handler=None,
    )


def _is_resource_gone(error: BaseException) -> bool:
    if isinstance(error, ResourceGone):
        return True
    if isinstance(error, MediaLoadError):
        return _is_resource_gone(error.original_error)
    if isinstance(error, MediaLoadErrors):
        return any(_is_resource_gone(item) for item in error.errors)
    return False


async def on_error(context: ScrapeErrorContext) -> ErrorAction:
    logger.error(
        "URL: %s, ERROR: %s, Attempt: %s/%s",
        context.url,
        context.error,
        context.attempt,
        context.max_attempts,
    )

    if _is_resource_gone(context.error):
        return ErrorAction.SKIP

    return ErrorAction.RETRY


async def get_html_content(core: BaseCore, url: str) -> str:
    try:
        return await core.fetch_text(url)

    except HTTPStatusError as e:
        if e.status_code == 404:
            raise NotFound(f"Server returned 404 for: {url}") from e
        raise NetworkError(str(e)) from e

    except (NetworkRequestError, RequestRetriesExhausted) as e:
        raise NetworkError(str(e)) from e

    except InvalidProxy as e:
        raise ProxyError(str(e)) from e

    except BotProtectionDetected as e:
        raise BotDetection(str(e)) from e

    except UnknownError as e:
        raise UnknownNetworkError(str(e)) from e


@dataclass(kw_only=True, slots=True)
class Video(BaseMedia):
    url: str
    core: BaseCore
    title: str | None = media_field("html")
    likes: str | None = media_field("html")
    dislikes: str | None = media_field("html")
    publish_date: str | None = media_field("html")
    views: str | None = media_field("html")
    author: str | None = media_field("html")
    thumbnail: str | None = media_field("html")
    length: str | None = media_field("html")
    categories: list[str] | None = media_field("html")
    tags: list[str] | None = media_field("html")
    cdn_urls: list[str] | None = media_field("html")

    # Optional
    rating: str | None = None

    loader_methods: ClassVar[dict[str, str]] = {"html": "_load_html"}

    async def _load_html(self) -> dict[str, object]:
        html_content = await get_html_content(core=self.core, url=self.url)
        return await asyncio.to_thread(self._extract_html, html_content)

    @staticmethod
    def _extract_html(html_content: str) -> dict:
        parser = LexborHTMLParser(html_content)
        title = parser.css_first("h1.big-title-truncate.m-t-0").text(strip=True)
        likes = parser.css_first("a.videoLikeBtn.mr-2").text(strip=True)
        dislikes = parser.css_first("a.videoDisLikeBtn").text(strip=True)
        publish_date = parser.css_first("div.pull-right.big-views-xs.font-weight-bold.visible-xs.pt-0").css_first("span").text(strip=True)
        views = parser.css_first("div.pull-right.big-views-xs.font-weight-bold.visible-xs.pt-0").css("span")[1].text(strip=True)
        author = parser.css_first("div.pull-left.user-container").css_first("a.standard-link").text(strip=True)
        thumbnail = REGEX_THUMBNAIL.search(html_content).group(1)
        length = REGEX_VIDEO_DURATION.search(html_content).group(1)

        a_tags = parser.css("div.m-t-10.p-bold.overflow-hidden")[1].css("a")
        categories = [tag.text(strip=True) for tag in a_tags]

        a_tags = parser.css_first("div.videoTagsSpace.m-t-10.m-b-15.p-bold.overflow-hidden").css("a")
        tags = [tag.text(strip=True) for tag in a_tags]

        urls = parser.css('source[src][title][type="video/mp4"]')
        cdn_urls = [tag.attributes.get("src") for tag in urls]

        return {
            "title": title,
            "likes": likes,
            "dislikes": dislikes,
            "publish_date": publish_date,
            "views": views,
            "author": author,
            "thumbnail": thumbnail,
            "length": length,
            "categories": categories,
            "tags": tags,
            "cdn_urls": cdn_urls
        }

    async def download(self, configuration: DownloadConfigRAW):
        await self.load_fields("cdn_urls", "title")
        cdn_urls = self.cdn_urls
        config = configuration

        if len(cdn_urls) == 2: # There's no further quality specification other than HD / SD...
            if config.quality == "hd":
                download_url = cdn_urls[1] # HD quality

            else:
                download_url = cdn_urls[0] # SD quality

        else:
            download_url = cdn_urls[0] # Video is only available in SD quality

        if not config.no_title:
            config.path = os.path.join(config.path, f"{self.title}.mp4")

        try:
            await self.core.legacy_download(url=download_url, configuration=config)
            return True

        except Exception as e:
            return DownloadFailed(str(e))

    def video_qualities(self) -> list[int]:
        if len(self.cdn_urls) == 1:
            return [480]

        elif len(self.cdn_urls) == 2:
            return [480, 720]

        elif len(self.cdn_urls) >= 3:
            print(f"TELL ME IMMEDIATELY ON GITHUB WHAT YOU DID, LIKE RIGHT NOW!: {self.cdn_urls}")

        return []


@dataclass(kw_only=True, slots=True)
class Album(BaseMedia):
    url: str
    core: BaseCore
    title: str | None = media_field("html")
    total_pages_count: int | None = media_field("html")

    loader_methods: ClassVar[dict[str, str]] = {"html": "_load_html"}

    async def _load_html(self) -> dict[str, object]:
        html_content = await get_html_content(core=self.core, url=self.url)
        return await asyncio.to_thread(self._extract_data, html_content)

    @staticmethod
    def _extract_data(html_content: str) -> dict:
        parser = LexborHTMLParser(html_content)
        title = parser.css_first("h1.pull-left").text(strip=True)
        stuff = parser.css("div.panel-body")[2]
        start = int(stuff.css_first("span.text-white").text(strip=True))
        end = int(stuff.css("span.text-white")[1].text(strip=True))
        total = int(stuff.css("span.text-white")[2].text(strip=True))

        per_page = end - start + 1
        if per_page <= 0:
            raise ValueError(f"Invalid range: start={start}, end={end}")

        total_pages_count = math.ceil(total / per_page)

        return {
            "title": title,
            "total_pages_count": total_pages_count,
        }

    @staticmethod
    def _scrape_images(html_content: str) -> list[str]:
        soup = LexborHTMLParser(html_content)
        divs = soup.css("div.thumb-overlay.album-thumb")
        a_tags = [div.css_first("a") for div in divs]
        urls = [a.attributes.get("href") for a in a_tags]

        return urls

    async def get_images_by_page(self, page: int = 1) -> list:
        total_pages_count = await self.get_field("total_pages_count")
        if page > total_pages_count:
            raise "This page doesn't exist"

        url = f"{self.url}?page={page}"
        html = await get_html_content(core=self.core, url=url)
        assert isinstance(html, str)
        images = await asyncio.to_thread(self._scrape_images, html)

        return images

    async def get_all_images(self) -> list:
        all_images = []
        total_pages_count = await self.get_field("total_pages_count")
        page_urls = [f"{self.url}?page={page}" for page in range(1, total_pages_count + 1)]

        if page_urls:
            pages_html = await asyncio.gather(*[get_html_content(core=self.core, url=url) for url in page_urls])
            for html in pages_html:
                all_images.extend(await asyncio.to_thread(self._scrape_images, html))

        return all_images


class Client:
    def __init__(self, core: BaseCore = BaseCore()):
        self.core = core
        self.core.initialize_session()
        self.helper = Helper(core=self.core, constructor=Video)

    async def get_video(self, url: str, load_html: bool = True) -> Video:
        video = Video(url=url, core=self.core)
        if load_html:
            await video.load_sources("html")
        return video

    async def get_album(self, url: str, load_html: bool = True) -> Album:
        album = Album(url=url, core=self.core)
        if load_html:
            await album.load_sources("html")
        return album

    async def search(
        self,
        query: str,
        pages: int = 5,
        iterator_config: IteratorConfig | None = None,
    ) -> AsyncGenerator[ScrapeResult[Video], None]:
        query = query.replace(" ", "+")
        page_urls = [f"https://xfreehd.com/search?search_query={query}&search_type=videos&page={page}" for page in range(1, pages + 1)]

        if iterator_config is None:
            iterator_config = make_iterator_config()

        stream = self.helper.iterator(
            target_page_urls=page_urls,
            item_extractor=extractor_search,
            iterator_config=iterator_config,
        )
        async with stream:
            async for scrape_result in stream:
                yield scrape_result
