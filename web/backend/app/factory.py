from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.exporters import build_default_exporters
from app.providers import build_default_registry
from app.routers import mount_routers


def create_app() -> FastAPI:
    providers = build_default_registry()
    exporters = build_default_exporters()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.providers = providers
        app.state.exporters = exporters
        await providers.startup_all()
        try:
            yield
        finally:
            await providers.shutdown_all()

    app = FastAPI(
        title="Media Browser API",
        version="1.1.0",
        description="Modular provider/exporter API for the React GUI",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    mount_routers(app)
    return app
