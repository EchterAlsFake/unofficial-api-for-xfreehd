"""
Copyright (C) 2025-2026 Johannes Habel
Licensed under LGPLv3

If you haven't received the license with this library, see: https://www.gnu.org/licenses/lgpl-3.0.en.html
Only use this library under your local laws. I do not endorse any copyright infringement.
"""
import math
import asyncio
import logging
import argparse
import urllib.parse

from xfreehd_api.modules import errors as provider_errors
from base_api.modules.provider import fetch_content, download_errors, prepare_download_config
from base_api.modules.logger import configure_app_logging, get_logger

from base_api.modules.static_functions import str_to_bool

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
    make_iterator_config,
    is_resource_gone,
    default_on_error,
    scrape_stream,
)
from base_api.modules.errors import ResourceGone

from xfreehd_api.modules.consts import extractor_search
from xfreehd_api.modules.errors import (NetworkError, NotFound, UnknownNetworkError, BotDetection, ProxyError,
                                        DownloadFailed)


logger = get_logger(__name__)

SCRAPE_RETRY_POLICY = RetryPolicy(max_attempts=3)

_is_resource_gone = is_resource_gone
on_error = default_on_error



async def get_html_content(core: BaseCore, url: str, *, owner=None) -> str:
    return await fetch_content(core, url, logger=logger, owner=owner,
                               error_types=provider_errors)


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
    author_thumbnail: str | None = media_field("html")
    author_url: str | None = media_field("html")
    author_subscribers: str | None = media_field("html")
    thumbnail: str | None = media_field("html")
    length: str | None = media_field("html")
    categories: list[str] | None = media_field("html")
    tags: list[str] | None = media_field("html")
    cdn_urls: list[str] | None = media_field("html")
    embed_url: str | None = media_field("html")

    # Optional / Loaded
    rating: str | None = media_field("html")

    loader_methods: ClassVar[dict[str, str]] = {"html": "_load_html"}

    async def _load_html(self) -> dict[str, object]:
        html_content = await get_html_content(core=self.core, url=self.url, owner=self)
        return await asyncio.to_thread(self._extract_html, html_content)

    @staticmethod
    def _extract_html(html_content: str) -> dict:
        parser = LexborHTMLParser(html_content)
        if "This Video Is No Longer Available." in html_content:
            raise ResourceGone("Video is no longer available")

        # Title: h1 -> meta og/twitter -> share link -> player data-target slug
        title = None
        h1_el = parser.css_first("h1.big-title-truncate, h1")
        if h1_el and h1_el.text(strip=True):
            title = h1_el.text(strip=True)
        if not title:
            og_title = parser.css_first('meta[property="og:title"], meta[name="twitter:title"]')
            if og_title and og_title.attributes.get("content"):
                title = og_title.attributes.get("content").strip()
        if not title:
            reddit_el = parser.css_first('a[href*="reddit.com/submit"]')
            if reddit_el and "title=" in reddit_el.attributes.get("href", ""):
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(reddit_el.attributes.get("href")).query)
                reddit_title = qs.get("title", [""])[0]
                if "|" in reddit_title:
                    title = reddit_title.split("|")[0].strip()
                elif reddit_title:
                    title = reddit_title.strip()
        if not title:
            video_el = parser.css_first("video#hdPlayer, video")
            if video_el and video_el.attributes.get("data-target"):
                slug = video_el.attributes.get("data-target").rstrip("/").split("/")[-1]
                title = slug.replace("-", " ").title()

        # Likes & Dislikes
        like_btn = parser.css_first("a.videoLikeBtn, [id^='vote_like_']")
        likes = None
        if like_btn:
            num_el = like_btn.css_first("span.num")
            likes = num_el.text(strip=True) if num_el else like_btn.text(strip=True)

        dislike_btn = parser.css_first("a.videoDisLikeBtn, [id^='vote_dislike_']")
        dislikes = None
        if dislike_btn:
            num_el = dislike_btn.css_first("span.num")
            dislikes = num_el.text(strip=True) if num_el else dislike_btn.text(strip=True)

        # Publish date & Views
        publish_date = None
        views = None
        views_box = parser.css_first("div.big-views-xs, div.big-views")
        if views_box:
            spans = views_box.css("span")
            if spans:
                publish_date = spans[0].text(strip=True).rstrip(",").strip()
            if len(spans) > 1:
                views = spans[1].text(strip=True)

        # Author metadata
        author_el = parser.css_first("div.user-container a.standard-link, div.user-container strong, a[href*='/user/'] strong")
        author = author_el.text(strip=True) if author_el else None

        author_link = parser.css_first("div.user-container a[href*='/user/'], a[href*='/user/']")
        author_url = author_link.attributes.get("href") if author_link else None

        avatar_el = parser.css_first("div.user-container img.medium-avatar, div.user-container img")
        author_thumbnail = avatar_el.attributes.get("src") if avatar_el else None

        sub_badge = parser.css_first("div.user-container span.sbadge, span[class*='sbadge']")
        author_subscribers = sub_badge.text(strip=True) if sub_badge else None

        # Video Thumbnail
        thumbnail = None
        video_el = parser.css_first("video#hdPlayer, video")
        if video_el and video_el.attributes.get("data-img"):
            thumbnail = video_el.attributes.get("data-img")
        if not thumbnail:
            og_img = parser.css_first('meta[property="og:image"], meta[name="twitter:image"]')
            if og_img and og_img.attributes.get("content"):
                thumbnail = og_img.attributes.get("content")

        # Duration / Length
        length = None
        meta_dur = parser.css_first('meta[property="og:video:duration"]')
        if meta_dur and meta_dur.attributes.get("content"):
            length = meta_dur.attributes.get("content").strip()
        if not length and video_el and video_el.attributes.get("data-vtt"):
            vtt = video_el.attributes.get("data-vtt")
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(vtt).query)
            if "time" in qs:
                length = qs["time"][0]

        # Categories
        categories = []
        cat_container = None
        for div in parser.css("div.p-bold"):
            if "Categories:" in div.text():
                cat_container = div
                break
        if cat_container:
            categories = [a.text(strip=True) for a in cat_container.css("a") if a.text(strip=True)]
        if not categories:
            categories = [a.text(strip=True) for a in parser.css('a[href*="/videos/"]') if a.text(strip=True)]

        # Tags
        tags = []
        tag_nodes = parser.css("div.videoTagsSpace a, a.tag")
        if tag_nodes:
            for t in tag_nodes:
                text = t.text(strip=True)
                if text and text not in tags:
                    tags.append(text)
        if not tags:
            meta_tags = parser.css('meta[property="video:tag"]')
            for m in meta_tags:
                c = m.attributes.get("content")
                if c and c.strip() and c.strip() not in tags:
                    tags.append(c.strip())

        # CDN URLs (deduplicated, order preserved)
        cdn_urls = []
        for tag in parser.css('video source[src], source[src]'):
            src = tag.attributes.get("src")
            if src and src not in cdn_urls:
                cdn_urls.append(src)

        # Embed URL
        embed_url = None
        embed_textarea = parser.css_first("textarea#video_embed_code")
        if embed_textarea and embed_textarea.text():
            iframe_parser = LexborHTMLParser(embed_textarea.text())
            iframe = iframe_parser.css_first("iframe")
            if iframe and iframe.attributes.get("src"):
                embed_url = iframe.attributes.get("src")
        if not embed_url:
            og_embed = parser.css_first('meta[property="og:video:url"], meta[name="twitter:player"]')
            if og_embed and og_embed.attributes.get("content"):
                embed_url = og_embed.attributes.get("content")

        # Rating percentage computed from likes and dislikes
        rating = None
        if likes and dislikes:
            try:
                l_val = int(likes)
                d_val = int(dislikes)
                if l_val + d_val > 0:
                    rating = f"{round((l_val / (l_val + d_val)) * 100)}%"
            except ValueError:
                pass

        return {
            "title": title,
            "likes": likes,
            "dislikes": dislikes,
            "publish_date": publish_date,
            "views": views,
            "author": author,
            "author_url": author_url,
            "author_thumbnail": author_thumbnail,
            "author_subscribers": author_subscribers,
            "thumbnail": thumbnail,
            "length": length,
            "categories": categories,
            "tags": tags,
            "cdn_urls": cdn_urls,
            "embed_url": embed_url,
            "rating": rating,
        }

    @download_errors(DownloadFailed)
    async def download(self, configuration: DownloadConfigRAW):
        await self.load_fields("cdn_urls", "title")
        cdn_urls = self.cdn_urls
        config = prepare_download_config(configuration, self.title)

        if not cdn_urls:
            raise DownloadFailed(f"No CDN URLs available to download for {self.url}")

        if len(cdn_urls) == 2:  # There's no further quality specification other than HD / SD...
            if config.quality in ("hd", "best"):
                download_url = cdn_urls[1]  # HD quality
            else:
                download_url = cdn_urls[0]  # SD quality
        else:
            download_url = cdn_urls[0]  # Video is only available in SD quality


        return await self.core.legacy_download(url=download_url, configuration=config)

    def video_qualities(self) -> list[int]:
        if not self.cdn_urls:
            return []
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
        html_content = await get_html_content(core=self.core, url=self.url, owner=self)
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
            raise NotFound(f"Album page {page} does not exist for {self.url}; total pages={total_pages_count}")

        url = f"{self.url}?page={page}"
        html = await get_html_content(core=self.core, url=url, owner=self)
        assert isinstance(html, str)
        images = await asyncio.to_thread(self._scrape_images, html)

        return images

    async def get_all_images(self) -> list:
        all_images = []
        total_pages_count = await self.get_field("total_pages_count")
        page_urls = [f"{self.url}?page={page}" for page in range(1, total_pages_count + 1)]

        if page_urls:
            pages_html = await asyncio.gather(*[get_html_content(core=self.core, url=url, owner=self) for url in page_urls])
            for html in pages_html:
                all_images.extend(await asyncio.to_thread(self._scrape_images, html))

        return all_images


class Client:
    def __init__(self, core: BaseCore | None = None):
        if core is None:
            core = BaseCore()
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

    def search(
        self,
        query: str,
        pages: int = 5,
        iterator_config: IteratorConfig | None = None,
    ) -> AsyncGenerator[ScrapeResult[Video], None]:
        query = query.replace(" ", "+")
        page_urls = [f"https://xfreehd.com/search?search_query={query}&search_type=videos&page={page}" for page in range(1, pages + 1)]
        return scrape_stream(
            core=self.core,
            constructor=Video,
            target_page_urls=page_urls,
            item_extractor=extractor_search,
            iterator_config=iterator_config,
        )



def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="XFreeHD API Command Line Interface")
    parser.add_argument("--download", metavar="URL", type=str, help="URL to download from")
    parser.add_argument("--quality", metavar="best|half|worst", type=str, default="best", help="The video quality (best, half, worst)")
    parser.add_argument("--file", metavar="FILE", type=str, help="(Optional) Specify a file with URLs (separated with new lines)")
    parser.add_argument("--output", metavar="DIR", type=str, required=True, help="The output path (with filename or directory)")
    parser.add_argument("--no-title", metavar="True,False", type=str, nargs="?", const="True", default="False",
                        help="Whether to apply video title automatically to output path or not")
    return parser


async def run_main(args_list: list[str] | None = None):
    parser = create_parser()
    args = parser.parse_args(args_list)
    no_title = str_to_bool(args.no_title) if isinstance(args.no_title, str) else bool(args.no_title)
    config = DownloadConfigRAW(quality=args.quality, path=args.output, no_title=no_title)

    urls: list[str] = []
    if args.download:
        urls.append(args.download)
    if args.file:
        with open(args.file, "r") as f:
            urls.extend([line.strip() for line in f if line.strip()])

    if not urls:
        parser.print_help()
        return

    client = Client()
    for url in urls:
        print(f"Fetching video information for: {url}")
        try:
            video = await client.get_video(url, load_html=True)
            title = getattr(video, "title", None) or url
            print(f"Starting download for: {title}")
            await video.download(configuration=config)
            print(f"Download complete: {title}")
        except Exception as e:
            logger.exception("CLI failed while processing %s", url)
            print(f"Error downloading {url}: {e}")


def main():
    configure_app_logging(level=logging.INFO)
    try:
        asyncio.run(run_main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")


if __name__ == "__main__":
    main()
