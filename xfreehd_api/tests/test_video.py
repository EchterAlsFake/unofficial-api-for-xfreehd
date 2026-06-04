from ..xfreehd_api import Client
import pytest


@pytest.mark.asyncio
async def test_all():
    client = Client()
    url = "https://beta.xfreehd.com/video/929816/tap-out-pmv"
    video = await client.get_video(url)
    assert isinstance(video.title, str) and len(video.title) > 0
    assert isinstance(video.likes, str) and len(video.likes) > 0
    assert isinstance(video.dislikes, str) and len(video.dislikes) > 0
    assert isinstance(video.publish_date, str) and len(video.publish_date) > 0
    assert isinstance(video.views, str) and len(video.views) > 0
    assert isinstance(video.categories, list) and len(video.categories) > 0
    assert isinstance(video.tags, list) and len(video.tags) > 0
    assert isinstance(video.author, str) and len(video.author) > 0
    assert isinstance(video.thumbnail, str) and len(video.thumbnail) > 0
    assert isinstance(video.cdn_urls, list) and len(video.cdn_urls) > 0
    assert await video.download(quality="sd") is True
    assert await video.download(quality="hd") is True
