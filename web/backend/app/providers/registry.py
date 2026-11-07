from __future__ import annotations

from fastapi import HTTPException

from app.providers.base import MediaProvider
from app.schemas import ProviderInfo


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, MediaProvider] = {}
        self._default: str | None = None

    def register(self, provider: MediaProvider, *, default: bool = False) -> None:
        self._providers[provider.id] = provider
        if default or self._default is None:
            self._default = provider.id

    def get(self, provider_id: str | None = None) -> MediaProvider:
        key = provider_id or self._default
        if not key or key not in self._providers:
            raise HTTPException(
                404,
                f"Unknown provider '{provider_id}'. Available: {list(self._providers)}",
            )
        return self._providers[key]

    @property
    def default_id(self) -> str | None:
        return self._default

    def list(self) -> list[ProviderInfo]:
        return [
            ProviderInfo(
                id=p.id,
                name=p.name,
                description=p.description,
                capabilities=list(p.capabilities),
                filters=p.filters(),
            )
            for p in self._providers.values()
        ]

    async def startup_all(self) -> None:
        for provider in self._providers.values():
            await provider.startup()

    async def shutdown_all(self) -> None:
        for provider in self._providers.values():
            await provider.shutdown()


def build_default_registry() -> ProviderRegistry:
    """Wire built-in providers. External packages can call register() later."""
    from app.providers.beeg import BeegProvider
    from app.providers.missav import MissAVProvider
    from app.providers.xfreehd import XFreeHDProvider
    from app.providers.xnxx import XNXXProvider

    registry = ProviderRegistry()
    registry.register(XFreeHDProvider(), default=True)
    registry.register(MissAVProvider())
    registry.register(XNXXProvider())
    registry.register(BeegProvider())
    return registry
