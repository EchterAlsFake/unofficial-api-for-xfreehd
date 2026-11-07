from fastapi import FastAPI

from app.routers import meta, playlist, proxy, search, video


def mount_routers(app: FastAPI) -> None:
    app.include_router(meta.router)
    app.include_router(search.router)
    app.include_router(video.router)
    app.include_router(playlist.router)
    app.include_router(proxy.router)
