"""
Copyright (C) 2025-2026 Johannes Habel
Licensed under LGPLv3

If you haven't received the license with this library, see: https://www.gnu.org/licenses/lgpl-3.0.en.html
Only use this library under your local laws. I do not endorse any copyright infringement.
"""
import asyncio

from bs4 import BeautifulSoup

try:
    from modules.consts import *
except (ModuleNotFoundError, ImportError):
    from .modules.consts import *


import math
import os.path
import logging
import traceback
import threading

from typing import Optional
from functools import cached_property
from base_api import BaseCore, setup_logger

try:
    import lxml
    parser = "lxml"

except (ModuleNotFoundError, ImportError):
    parser = "html.parser"


class Video:
    def __init__(self, url: str, core: Optional[BaseCore] = None, html_content: str = None):
        self.url = url
        self.core = core
        self.html_content = html_content
        self.soup: Optional[BeautifulSoup] = None
        self.logger = setup_logger(name="XFreeHD API - [Video]", log_file=None, level=logging.ERROR)

    async def init(self):
        if not self.html_content:
            self.html_content = await self.get_html_content()

        self.soup = BeautifulSoup(self.html_content, parser)
        return self

    async def get_html_content(self) -> str:
        return await self.core.fetch(self.url)

    def enable_logging(self, log_file: str = None, level = None, log_ip: str = None, log_port: int = None):
        self.logger = setup_logger(name="XFreeHD API - [Video]", log_file=log_file, level=level, http_ip=log_ip, http_port=log_port)

    @cached_property
    def title(self) -> str:
        return self.soup.find("h1", class_="big-title-truncate m-t-0").text

    @cached_property
    def likes(self) -> str:
        return self.soup.find("a", class_="videoLikeBtn mr-2").text.strip()

    @cached_property
    def dislikes(self) -> str:
        return self.soup.find("a", class_="videoDisLikeBtn").text.strip()

    @cached_property
    def publish_date(self) -> str:
        return self.soup.find("div", class_="pull-right big-views-xs font-weight-bold visible-xs pt-0").find("span").text.strip()

    @cached_property
    def views(self) -> str:
        return self.soup.find("div", class_="pull-right big-views-xs font-weight-bold visible-xs pt-0").find_all("span")[1].text.strip()

    @cached_property
    def categories(self) -> list:
        a_tags = self.soup.find_all("div", class_="m-t-10 p-bold overflow-hidden")[1].find_all("a")
        return [tag.text.strip() for tag in a_tags]

    @cached_property
    def tags(self) -> list:
        a_tags = self.soup.find("div", class_="videoTagsSpace m-t-10 m-b-15 p-bold overflow-hidden").find_all("a")
        return [tag.text.strip() for tag in a_tags]

    @cached_property
    def author(self) -> str:
        return self.soup.find("div", class_="pull-left user-container").find("a", class_="standard-link").text.strip()

    @cached_property
    def thumbnail(self) -> str:
        return REGEX_THUMBNAIL.search(self.html_content).group(1)

    @cached_property
    def length(self) -> str:
        return REGEX_VIDEO_DURATION.search(self.html_content).group(1)

    @cached_property
    def video_qualities(self) -> list:
        # This might not be perfectly accurate, but I just need this working for Porn Fetch, so this is fine

        if len(self.cdn_urls) == 2:
            qualities = [480, 720] # HD should include 480 and 720 as to my definitions of what "HD" is

        elif len(self.cdn_urls) == 1:
            qualities = [480] # SD should be like 480 idk

        else:
            qualities = []

        return qualities

    @cached_property
    def cdn_urls(self) -> list:
        tags = self.soup.find_all("source", attrs={"src": True, "title": True, "type": "video/mp4"})
        urls = [tag.get("src") for tag in tags]
        return urls

    async def download(self, quality: str = "hd", no_title: bool = False, path="./", callback=None, stop_event: threading.Event = None):
        cdn_urls = self.cdn_urls

        if len(cdn_urls) == 2: # There's no further quality specification other than HD / SD...
            if quality == "hd":
                download_url = cdn_urls[1] # HD quality

            else:
                download_url = cdn_urls[0] # SD quality

        else:
            download_url = cdn_urls[0] # Video is only available in SD quality

        if no_title is False:
            path = os.path.join(path, f"{self.title}.mp4")

        try:
            await self.core.legacy_download(url=download_url, path=path, callback=callback, stop_event=stop_event)
            return True

        except Exception:
            error = traceback.format_exc()
            self.logger.error(error)
            return False


class Album:
    def __init__(self, url: str, core: Optional[BaseCore] = None, html_content: str = None):
        self.url = url
        self.core = core
        self.html_content = html_content
        self.soup: Optional[BeautifulSoup] = None
        self.logger = setup_logger(name="XFreeHD API - [Album]", log_file=None, level=logging.ERROR)


    async def init(self):
        if not self.html_content:
            self.html_content = await self.get_html_content(self.url)
          
        self.soup = BeautifulSoup(self.html_content, parser)
        return self

    async def get_html_content(self, url) -> str:
        return await self.core.fetch(url)

    def enable_logging(self, log_file: str = None, level = None, log_ip: str = None, log_port: int = None):
        self.logger = setup_logger(name="XFreeHD API - [Album]", log_file=log_file, level=level, http_ip=log_ip, http_port=log_port)

    @cached_property
    def title(self) -> str:
        return self.soup.find("h1", class_="pull-left").text.strip()

    @cached_property
    def total_pages_count(self) -> int:
        """
        Calculates the total amount of pages
        """
        soup = BeautifulSoup(self.html_content, parser)
        text = soup.find("div", class_="panel panel-default").find("div",class_="panel-body").text.strip()

        start = int(REGEX_ALBUM_START.search(text).group(1))
        end = int(REGEX_ALBUM_END.search(text).group(1))
        total = int(REGEX_ALBUM_TOTAL.search(text).group(1))

        per_page = end - start + 1
        if per_page <= 0:
            raise ValueError(f"Invalid range: start={start}, end={end}")

        return math.ceil(total / per_page)

    async def _scrape_images(self, html: str) -> list:
        soup = BeautifulSoup(html, parser)
        divs = soup.find_all("div", class_="thumb-overlay album-thumb")
        a_tags = [div.find("a") for div in divs]
        urls = [a.get("href") for a in a_tags]

        return urls

    async def get_images_by_page(self, page: int = None) -> list:
        if page > self.total_pages_count:
            raise "This page doesn't exist"

        if page == 1:
            images = self._scrape_images(self.html_content)

        else:
            url = f"{self.url}?page={page}"
            html = await self.core.fetch(url)
            images = await self._scrape_images(html)

        return images

    async def get_all_images(self) -> list:
        all_images = []

        all_images.extend(await self._scrape_images(self.html_content))
        page_urls = [f"{self.url}?page={page}" for page in range(2, self.total_pages_count + 1)]

        if page_urls:
            pages_html = await asyncio.gather(*[self.get_html_content(url) for url in page_urls])
            for html in pages_html:
                all_images.extend(await self._scrape_images(html))

        return all_images


class Client:
    def __init__(self, core: Optional[BaseCore] = None):
        self.core = core or BaseCore()
        self.core.initialize_session()
        self.logger = setup_logger(name="XFreeHD API - [Client]", log_file=None, level=logging.ERROR)

    def enable_logging(self, log_file: str = None, level = None, log_ip: str = None, log_port: int = None):
        self.logger = setup_logger(name="XFreeHD API - [Client]", log_file=log_file, level=level, http_ip=log_ip, http_port=log_port)

    async def get_video(self, url: str) -> Video:
        video = Video(url=url, core=self.core)
        return await video.init()

    async def get_album(self, url: str) -> Album:
        album = Album(url=url, core=self.core)
        return await album.init()
