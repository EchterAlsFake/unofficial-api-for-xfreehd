"""
Example stub for adding another media source.

1. Copy to `app/providers/mysite/provider.py` and implement the methods
2. Register in `build_default_registry()`:

       from app.providers.mysite import MySiteProvider
       registry.register(MySiteProvider())

Routers stay untouched — `/api/search?provider=mysite` picks it up via the registry.
"""

from __future__ import annotations

from typing import Any, AsyncIterator

from app.schemas import FilterField, MediaItem


class ExampleStubProvider:
    id = "example"
    name = "Example Site"
    description = "Stub — replace with a real scraper"

    @property
    def capabilities(self) -> list[str]:
        return ["search", "detail", "resolve_stream"]

    def filters(self) -> list[FilterField]:
        return []

    async def startup(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None

    async def search(
        self,
        query: str,
        *,
        filters: dict[str, Any] | None = None,
    ) -> AsyncIterator[MediaItem]:
        _ = (query, filters)
        if False:  # pragma: no cover — keeps this an async generator
            yield MediaItem(provider=self.id, url="")

    async def get_media(self, url: str) -> MediaItem:
        raise NotImplementedError(url)

    async def resolve_stream(self, url: str, *, quality: str = "best") -> tuple[str, str | None]:
        raise NotImplementedError((url, quality))
