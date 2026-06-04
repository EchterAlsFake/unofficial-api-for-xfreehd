from ..xfreehd_api import Client
import pytest

@pytest.mark.asyncio
async def test_images():
    client = Client()
    url = "https://beta.xfreehd.com/album/14805/woman-boy-18-nudists"
    album = await client.get_album(url)

    images = await album.get_all_images()
    assert isinstance(images, list)
    assert len(images) > 0

    images = await album.get_images_by_page(page=2)
    assert isinstance(images, list)
    assert len(images) > 0