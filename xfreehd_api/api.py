"""
Copyright (C) 2025-2026 Johannes Habel
Licensed under LGPLv3

If you haven't received the license with this library, see: https://www.gnu.org/licenses/lgpl-3.0.en.html
Only use this library under your local laws. I do not endorse any copyright infringement.
"""
import math
import asyncio
import os.path

from curl_cffi import Response
from dataclasses import dataclass, fields
from selectolax.lexbor import LexborHTMLParser
from base_api import BaseCore, BaseMedia, DownloadConfigRAW
from base_api.modules.errors import NetworkRequestError, InvalidProxy, BotProtectionDetected, UnknownError

from xfreehd_api.modules.consts import REGEX_THUMBNAIL, REGEX_VIDEO_DURATION
from xfreehd_api.modules.errors import (NetworkError, NotFound, UnknownNetworkError, BotDetection, ProxyError,
                                        DownloadFailed)


async def get_html_content(core: BaseCore, url: str) -> str | None | dict:
    # What should I do here?
    try:
        content = await core.fetch(url)
        if isinstance(content, str):
            return content

        if isinstance(content, Response):
            if content.status_code == 404:
                raise NotFound(f"Server returned 404 for: {url}")

    except NetworkRequestError as e:
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
    title: str | None = None
    likes: str | None = None
    dislikes: str | None = None
    publish_date: str | None = None
    views: str | None = None
    author: str | None = None
    thumbnail: str | None = None
    length: str | None = None
    categories: list[str] | None = None
    tags: list[str] | None = None
    cdn_urls: list[str] | None = None

    async def _perform_load(self, api: bool, html: bool, anything_else: bool):
        if html:
            await asyncio.gather(self._fetch_html())

    async def _fetch_html(self):
        html_content = await get_html_content(core=self.core, url=self.url)
        assert isinstance(html_content, str)
        data: dict = await asyncio.to_thread(self._extract_html, html_content)

        allowed_fields = [field.name for field in fields(self)]
        for key, value in data.items():
            if key in allowed_fields:
                setattr(self, key, value)

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

        # This might not be perfectly accurate, but I just need this working for Porn Fetch, so this is fine
        if len(cdn_urls) == 2:
            qualities = [480, 720] # HD should include 480 and 720 as to my definitions of what "HD" is

        elif len(cdn_urls) == 1:
            qualities = [480] # SD should be like 480 idk

        else:
            qualities = []

        video_qualities = qualities

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
            "video_qualities": video_qualities,
            "cdn_urls": cdn_urls
        }

    async def download(self, configuration: DownloadConfigRAW):
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


@dataclass(kw_only=True, slots=True)
class Album(BaseMedia):
    url: str
    core: BaseCore
    title: str | None = None
    total_pages_count: int | None = None

    async def _perform_load(self, api: bool, html: bool, anything_else: bool):
        if html:
            await asyncio.gather(self._fetch_html())

    async def _fetch_html(self):
        html_content = await get_html_content(core=self.core, url=self.url)
        assert isinstance(html_content, str)
        data: dict = await asyncio.to_thread(self._extract_data, html_content)
        self.title = data.get("title")
        self.total_pages_count = data.get("total_pages_count") # Is this inefficient? Yes. Do I care? No.

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
        if page > self.total_pages_count:
            raise "This page doesn't exist"

        url = f"{self.url}?page={page}"
        html = await get_html_content(core=self.core, url=url)
        assert isinstance(html, str)
        images = await asyncio.to_thread(self._scrape_images, html)

        return images

    async def get_all_images(self) -> list:
        all_images = []
        page_urls = [f"{self.url}?page={page}" for page in range(1, self.total_pages_count + 1)]

        if page_urls:
            pages_html = await asyncio.gather(*[get_html_content(core=self.core, url=url) for url in page_urls])
            for html in pages_html:
                all_images.extend(await asyncio.to_thread(self._scrape_images, html))

        return all_images


class Client:
    def __init__(self, core: BaseCore = BaseCore()):
        self.core = core
        self.core.initialize_session()

    async def get_video(self, url: str, load_html: bool = True) -> Video:
        video = Video(url=url, core=self.core)
        return await video.load(html=load_html)

    async def get_album(self, url: str, load_html: bool = True) -> Album:
        album = Album(url=url, core=self.core)
        return await album.load(html=load_html)
