from __future__ import annotations

from fastapi import HTTPException

from app.exporters.base import PlaylistExporter
from app.exporters.m3u import M3UExporter
from app.schemas import ExporterInfo


class ExporterRegistry:
    def __init__(self) -> None:
        self._exporters: dict[str, PlaylistExporter] = {}

    def register(self, exporter: PlaylistExporter) -> None:
        self._exporters[exporter.id] = exporter

    def get(self, exporter_id: str) -> PlaylistExporter:
        if exporter_id not in self._exporters:
            raise HTTPException(
                404,
                f"Unknown exporter '{exporter_id}'. Available: {list(self._exporters)}",
            )
        return self._exporters[exporter_id]

    def list(self) -> list[ExporterInfo]:
        return [
            ExporterInfo(
                id=e.id,
                name=e.name,
                description=e.description,
                mime_type=e.mime_type,
                extension=e.extension,
            )
            for e in self._exporters.values()
        ]


def build_default_exporters() -> ExporterRegistry:
    registry = ExporterRegistry()
    registry.register(M3UExporter())
    # Future: registry.register(JsonExporter()), CsvExporter(), etc.
    return registry
