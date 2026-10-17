"""Offline regressions for URL identity, pagination and listing contracts."""

import unittest
from unittest.mock import AsyncMock, patch

from xfreehd_api import api as api


class EmptyStream:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration


class UrlHandlingTests(unittest.IsolatedAsyncioTestCase):
    async def test_album_pagination_replaces_page_and_removes_anchor(self):
        album = api.Album(url="https://beta.xfreehd.com/album/123/name?page=7&sort=new#photos", core=object())
        fetch = AsyncMock(return_value="<html></html>")
        with (
            patch.object(api, "get_html_content", fetch),
            patch.object(api.Album, "get_field", AsyncMock(return_value=3)),
        ):
            self.assertEqual(await album.get_images_by_page(2), [])
        self.assertEqual(fetch.call_args.kwargs["url"], "https://beta.xfreehd.com/album/123/name?sort=new&page=2")


if __name__ == "__main__":
    unittest.main()
