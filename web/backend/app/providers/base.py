from __future__ import annotations

from typing import Any, AsyncIterator, Protocol, runtime_checkable

from app.schemas import FilterField, MediaItem


@runtime_checkable
class MediaProvider(Protocol):
    """Contract for a media source. Add a new site by implementing this."""

    id: str
    name: str
    description: str

    @property
    def capabilities(self) -> list[str]:
        """e.g. search, detail, resolve_stream, album"""
        ...

    def filters(self) -> list[FilterField]:
        ...

    async def startup(self) -> None:
        ...

    async def shutdown(self) -> None:
        ...

    def search(
        self,
        query: str,
        *,
        filters: dict[str, Any] | None = None,
    ) -> AsyncIterator[MediaItem]:
        ...

    async def get_media(self, url: str) -> MediaItem:
        ...

    async def resolve_stream(self, url: str, *, quality: str = "best") -> tuple[str, str | None]:
        """Return (stream_url, title). Used by playlist exporters."""
        ...

    def playback_headers(self, stream_url: str | None = None) -> dict[str, str]:
        """HTTP headers media players should send when opening stream_url."""
        ...
