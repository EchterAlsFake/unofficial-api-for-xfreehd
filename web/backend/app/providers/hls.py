from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urljoin

import httpx

logger = logging.getLogger("xfreehd.web.providers.hls")


def _height(line_attrs: str) -> int:
    # RESOLUTION=1280x720 or NAME="720p"
    for part in line_attrs.split(","):
        part = part.strip()
        if part.upper().startswith("RESOLUTION="):
            res = part.split("=", 1)[1]
            if "x" in res.lower():
                try:
                    return int(res.lower().split("x")[1])
                except ValueError:
                    return 0
        if part.upper().startswith("NAME="):
            name = part.split("=", 1)[1].strip().strip('"').lower().rstrip("p")
            try:
                return int(name)
            except ValueError:
                return 0
    return 0


def _bandwidth(line_attrs: str) -> int:
    for part in line_attrs.split(","):
        part = part.strip()
        if part.upper().startswith("BANDWIDTH="):
            try:
                return int(part.split("=", 1)[1])
            except ValueError:
                return 0
    return 0


def pick_variant_url(master_text: str, master_url: str, quality: str = "best") -> str | None:
    """Pick a media-playlist URL from an HLS master according to quality preference."""
    lines = [ln.strip() for ln in master_text.splitlines() if ln.strip()]
    variants: list[tuple[int, int, str]] = []  # height, bandwidth, url

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#EXT-X-STREAM-INF:"):
            attrs = line.split(":", 1)[1]
            uri = lines[i + 1] if i + 1 < len(lines) and not lines[i + 1].startswith("#") else None
            if uri:
                variants.append((_height(attrs), _bandwidth(attrs), urljoin(master_url, uri)))
            i += 2
            continue
        i += 1

    if not variants:
        return None

    q = (quality or "best").lower().strip().rstrip("p")
    variants_sorted = sorted(variants, key=lambda v: (v[0], v[1]))

    if q in ("best", "highest", "max", "hd"):
        return variants_sorted[-1][2]
    if q in ("worst", "lowest", "min"):
        return variants_sorted[0][2]
    if q in ("half", "mid", "middle"):
        return variants_sorted[len(variants_sorted) // 2][2]

    try:
        target = int(q)
    except ValueError:
        return variants_sorted[-1][2]

    # Prefer exact height, else closest without going below if possible
    exact = [v for v in variants_sorted if v[0] == target]
    if exact:
        return exact[-1][2]
    above = [v for v in variants_sorted if v[0] >= target]
    if above:
        return above[0][2]
    return variants_sorted[-1][2]


async def resolve_hls_quality(
    master_url: str,
    *,
    quality: str = "best",
    headers: dict[str, str] | None = None,
    core: Any | None = None,
) -> str:
    """
    Resolve an HLS master URL to a specific quality media playlist.

    Prefers BaseCore.get_m3u8_by_quality when available; falls back to httpx parse.
    """
    if core is not None and hasattr(core, "get_m3u8_by_quality"):
        try:
            return await core.get_m3u8_by_quality(m3u8_url=master_url, quality=quality or "best")
        except Exception as exc:
            logger.warning("core.get_m3u8_by_quality failed (%s); falling back", exc)

    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        resp = await client.get(master_url, headers=headers or {})
        resp.raise_for_status()
        picked = pick_variant_url(resp.text, master_url, quality=quality or "best")
        if not picked:
            raise ValueError(f"No HLS variants in {master_url}")
        return picked
