"""Comprehensive edge-case and regression tests for xfreehd_api."""

import tempfile
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from base_api import DownloadConfigRAW, BaseCore
from base_api.modules.errors import DownloadFailed, NotFound, ResourceGone
from xfreehd_api.api import Client, Video, Album, run_main


SAMPLE_PRIVATE_HTML = """
<div class="row">
    <div class="col-lg-9">
        <h1 class="big-title-truncate">Exclusive Private Clip</h1>
        <div class="video-container video-private-container">
            <div class="vpheader"><img src="/images/private_Iocked.png"></div>
            <div class="vpfooter">This is a private video. You must be subscribers with <a href="/user/secret">secret</a></div>
        </div>
        <div class="pull-left user-container">
            <a href="https://beta.xfreehd.com/user/secret"><strong>secret</strong></a>
        </div>
    </div>
</div>
"""

SAMPLE_FORMATTED_RATING_HTML = """
<div class="row">
    <div class="col-lg-9">
        <h1>Formatted Rating Test</h1>
        <a class="videoLikeBtn"><span class="num">1.5K</span></a>
        <a class="videoDisLikeBtn"><span class="num">500</span></a>
        <div class="video-container">
            <video id="hdPlayer" data-img="https://image.xfreehd.com/thumb.jpg">
                <source src="https://lb.xfreehd.com/sd.mp4" title="SD">
                <source src="https://lb.xfreehd.com/hd.mp4" title="HD">
            </video>
        </div>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "VideoObject",
            "duration": "PT01H02M03S"
        }
        </script>
    </div>
</div>
"""

SAMPLE_ALBUM_HTML = """
<div class="container">
    <h1 class="pull-left">Test Album</h1>
    <div class="panel-body">Sidebar 1</div>
    <div class="panel-body">Sidebar 2</div>
    <div class="panel-body">
        Showing <span class="text-white">1</span> to <span class="text-white">12</span> of <span class="text-white">36</span> photos.
    </div>
    <div class="thumb-overlay album-thumb"><a href="https://xfreehd.com/photo/1/"></a></div>
    <div class="thumb-overlay album-thumb"><a href="https://xfreehd.com/photo/2/"></a></div>
</div>
"""


# -------------------------------------------------------------------------
# URL Normalization Tests
# -------------------------------------------------------------------------

def test_video_url_normalization():
    core = MagicMock(spec=BaseCore)

    # 1. Numeric ID
    v1 = Video(url="1092426", core=core)
    assert v1.video_id == "1092426"
    assert v1.url == "https://xfreehd.com/video/1092426"

    # 2. Relative path
    v2 = Video(url="/video/1092426/slug", core=core)
    assert v2.video_id == "1092426"
    assert v2.url == "https://xfreehd.com/video/1092426/slug"

    # 3. Embed URL
    v3 = Video(url="https://beta.xfreehd.com/embed/1092426", core=core)
    assert v3.video_id == "1092426"
    assert v3.url == "https://xfreehd.com/video/1092426"

    # 4. Standard full URL
    v4 = Video(url="https://xfreehd.com/video/1092426/test-title", core=core)
    assert v4.video_id == "1092426"
    assert v4.url == "https://xfreehd.com/video/1092426/test-title"


def test_album_url_normalization():
    core = MagicMock(spec=BaseCore)

    # 1. Numeric ID
    a1 = Album(url="17461", core=core)
    assert a1.album_id == "17461"
    assert a1.url == "https://xfreehd.com/album/17461"

    # 2. Relative path
    a2 = Album(url="/album/17461/gallery", core=core)
    assert a2.album_id == "17461"
    assert a2.url == "https://xfreehd.com/album/17461/gallery"

    # 3. Full URL
    a3 = Album(url="https://beta.xfreehd.com/album/17461/title", core=core)
    assert a3.album_id == "17461"


# -------------------------------------------------------------------------
# Video Parsing and Formatting Edge Cases
# -------------------------------------------------------------------------

def test_private_video_extraction():
    data = Video._extract_html(SAMPLE_PRIVATE_HTML)
    assert data["is_private"] is True
    assert data["cdn_urls"] == []
    assert data["title"] == "Exclusive Private Clip"
    assert data["author"] == "secret"


def test_formatted_rating_and_jsonld_duration():
    data = Video._extract_html(SAMPLE_FORMATTED_RATING_HTML)
    assert data["is_private"] is False
    assert data["likes"] == "1.5K"
    assert data["dislikes"] == "500"
    # 1500 / (1500 + 500) = 75%
    assert data["rating"] == "75%"
    # PT01H02M03S = 1*3600 + 2*60 + 3 = 3723s
    assert data["length"] == "3723"
    assert len(data["cdn_urls"]) == 2


def test_video_qualities_counts():
    core = MagicMock(spec=BaseCore)
    v = Video(url="https://xfreehd.com/video/1", core=core)

    v.cdn_urls = []
    assert v.video_qualities() == []

    v.cdn_urls = ["https://lb.xfreehd.com/1.mp4"]
    assert v.video_qualities() == [480]

    v.cdn_urls = ["https://lb.xfreehd.com/1.mp4", "https://lb.xfreehd.com/2.mp4"]
    assert v.video_qualities() == [480, 720]

    v.cdn_urls = ["https://lb.xfreehd.com/1.mp4", "https://lb.xfreehd.com/2.mp4", "https://lb.xfreehd.com/3.mp4"]
    assert v.video_qualities() == [480, 720, 1080]

    v.cdn_urls = [
        "https://lb.xfreehd.com/1.mp4",
        "https://lb.xfreehd.com/2.mp4",
        "https://lb.xfreehd.com/3.mp4",
        "https://lb.xfreehd.com/4.mp4",
    ]
    assert v.video_qualities() == [480, 720, 1080, 2160]


# -------------------------------------------------------------------------
# Download Quality Selection Edge Cases
# -------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_download_quality_selection():
    core = MagicMock(spec=BaseCore)
    core.legacy_download = AsyncMock(return_value=True)

    v = Video(url="https://xfreehd.com/video/1", core=core)
    v.title = "Sample"
    v.cdn_urls = [
        "https://lb.xfreehd.com/sd_480.mp4",
        "https://lb.xfreehd.com/hd_720.mp4",
        "https://lb.xfreehd.com/fhd_1080.mp4",
    ]

    # Best / HD / 1080 / 720
    await v.download(DownloadConfigRAW(quality="best", path="/tmp"))
    assert core.legacy_download.call_args.kwargs["url"] == "https://lb.xfreehd.com/fhd_1080.mp4"

    await v.download(DownloadConfigRAW(quality="1080", path="/tmp"))
    assert core.legacy_download.call_args.kwargs["url"] == "https://lb.xfreehd.com/fhd_1080.mp4"

    # Worst / SD / 480
    await v.download(DownloadConfigRAW(quality="worst", path="/tmp"))
    assert core.legacy_download.call_args.kwargs["url"] == "https://lb.xfreehd.com/sd_480.mp4"

    await v.download(DownloadConfigRAW(quality="480", path="/tmp"))
    assert core.legacy_download.call_args.kwargs["url"] == "https://lb.xfreehd.com/sd_480.mp4"

    # Half / middle
    await v.download(DownloadConfigRAW(quality="half", path="/tmp"))
    assert core.legacy_download.call_args.kwargs["url"] == "https://lb.xfreehd.com/hd_720.mp4"


@pytest.mark.asyncio
async def test_download_private_video_raises():
    core = MagicMock(spec=BaseCore)
    v = Video(url="https://xfreehd.com/video/1", core=core)
    v.title = "Private Clip"
    v.cdn_urls = []
    v.is_private = True

    with pytest.raises(DownloadFailed) as exc_info:
        await v.download(DownloadConfigRAW(quality="best", path="/tmp"))
    assert "private" in str(exc_info.value).lower()


# -------------------------------------------------------------------------
# Album Robustness Edge Cases
# -------------------------------------------------------------------------

def test_album_extract_data_structure():
    data = Album._extract_data(SAMPLE_ALBUM_HTML)
    assert data["title"] == "Test Album"
    assert data["total_pages_count"] == 3  # 36 / (12 - 1 + 1) = 3


def test_album_extract_data_empty_fallback():
    # Atypical HTML with no pagination
    html = "<html><body><h1>Minimal</h1></body></html>"
    data = Album._extract_data(html)
    assert data["title"] == "Minimal"
    assert data["total_pages_count"] == 1


def test_album_extract_gone():
    html = "<div>This Album Is No Longer Available.</div>"
    with pytest.raises(ResourceGone):
        Album._extract_data(html)


@pytest.mark.asyncio
async def test_album_invalid_page():
    core = MagicMock(spec=BaseCore)
    album = Album(url="https://xfreehd.com/album/1", core=core)
    album.total_pages_count = 2

    # Page 0
    with pytest.raises(ValueError):
        await album.get_images_by_page(0)

    # Page > total_pages_count
    with pytest.raises(NotFound):
        await album.get_images_by_page(3)


# -------------------------------------------------------------------------
# Client Lifecycle & Search Edge Cases
# -------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_client_async_context():
    client = Client()
    async with client as c:
        assert c.core is not None


@pytest.mark.asyncio
async def test_search_special_chars_and_filters():
    client = Client()
    # Ensure search with special characters & quotation does not raise an exception
    count = 0
    async for item in client.search("asian & blonde", pages=1, sort_by="mr"):
        count += 1
        assert item.item is not None
        assert item.item.url.startswith("http")
        if count >= 3:
            break
    assert count > 0


@pytest.mark.asyncio
async def test_search_empty_query():
    client = Client()
    # Non-existent query triggers 404 on server; scrape_stream should handle it cleanly
    results = []
    async for item in client.search("xyznonexistent9876543210qwerty", pages=1):
        results.append(item)
    assert len(results) == 0


# -------------------------------------------------------------------------
# CLI Edge Cases
# -------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cli_missing_file(capsys):
    await run_main(["--file", "/nonexistent_path/urls.txt", "--output", "/tmp"])
    captured = capsys.readouterr()
    assert "error reading file" in captured.out.lower() or "error" in captured.out.lower()
