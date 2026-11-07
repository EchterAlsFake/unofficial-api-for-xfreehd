from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FilterOption(BaseModel):
    value: str
    label: str


class FilterField(BaseModel):
    """Declarative search filter a provider exposes to the UI."""

    key: str
    label: str
    type: str = "select"  # select | number | text
    default: str | int | None = None
    options: list[FilterOption] = Field(default_factory=list)
    min: int | None = None
    max: int | None = None


class MediaItem(BaseModel):
    """Normalized media payload shared across providers."""

    provider: str
    url: str
    id: str | None = None
    title: str | None = None
    thumbnail: str | None = None
    length: str | None = None
    views: str | None = None
    rating: str | None = None
    author: str | None = None
    publish_date: str | None = None
    tags: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    stream_urls: list[str] = Field(default_factory=list)
    embed_url: str | None = None
    is_private: bool | None = None
    extras: dict[str, Any] = Field(default_factory=dict)


class ProviderInfo(BaseModel):
    id: str
    name: str
    description: str = ""
    capabilities: list[str] = Field(default_factory=list)
    filters: list[FilterField] = Field(default_factory=list)


class ExporterInfo(BaseModel):
    id: str
    name: str
    description: str = ""
    mime_type: str
    extension: str


class PlaylistItem(BaseModel):
    url: str
    title: str | None = None
    provider: str | None = None


class PlaylistRequest(BaseModel):
    items: list[PlaylistItem] = Field(default_factory=list)
    exporter: str = "m3u"
    quality: str = "best"
    resolve: bool = True
    provider: str | None = None
