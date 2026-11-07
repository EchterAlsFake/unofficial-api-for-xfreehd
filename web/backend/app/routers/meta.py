from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["meta"])


@router.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "eaf-media-browser-api",
        "ui": "http://127.0.0.1:5173",
        "health": "/api/health",
        "meta": "/api/meta",
        "docs": "/docs",
    }


@router.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/meta")
async def meta(request: Request) -> dict:
    providers = request.app.state.providers
    exporters = request.app.state.exporters
    return {
        "providers": [p.model_dump() for p in providers.list()],
        "exporters": [e.model_dump() for e in exporters.list()],
        "default_provider": providers.default_id,
    }
