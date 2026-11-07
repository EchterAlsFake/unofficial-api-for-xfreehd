from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from app.schemas import PlaylistItem


@dataclass(slots=True)
class PlaylistEntry:
    title: str
    url: str
    http_headers: dict[str, str] = field(default_factory=dict)


@runtime_checkable
class PlaylistExporter(Protocol):
    id: str
    name: str
    description: str
    mime_type: str
    extension: str

    def render(self, entries: list[PlaylistEntry]) -> str:
        ...


def normalize_items(items: list[PlaylistItem]) -> list[PlaylistItem]:
    return [i for i in items if i.url]
