"""Beeg tag search via the same externulls WebSocket index as beeg.com/search.

Ported from the local beeg.py worker (search_tags_ws + facts/tag listing).
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import socket
import ssl
import struct
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("xfreehd.web.providers.beeg.search")

SITE_URL = "https://beeg.com"
API_SEARCH_HOST = "search.externulls.com"
API_TAG_SLUG = "https://store.externulls.com/facts/tag?slug={slug}&limit={limit}&offset={offset}"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
PAGE_SIZE = 24
HTTP_HEADERS = {
    "User-Agent": USER_AGENT,
    "Referer": f"{SITE_URL}/",
    "Origin": SITE_URL,
    "Accept": "application/json, text/plain, */*",
}


def _ws_mask(payload: bytes) -> bytes:
    mask = os.urandom(4)
    return mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload))


def _ws_send_text(sock: ssl.SSLSocket, text: str) -> None:
    payload = text.encode("utf-8")
    header = bytearray([0x81])
    length = len(payload)
    if length < 126:
        header.append(0x80 | length)
    elif length < 65536:
        header.append(0x80 | 126)
        header.extend(struct.pack("!H", length))
    else:
        header.append(0x80 | 127)
        header.extend(struct.pack("!Q", length))
    sock.sendall(bytes(header) + _ws_mask(payload))


def _ws_recv_exact(sock: ssl.SSLSocket, leftover: bytes, count: int) -> tuple[bytes, bytes]:
    buf = leftover
    while len(buf) < count:
        chunk = sock.recv(max(count - len(buf), 4096))
        if not chunk:
            raise RuntimeError("Search WebSocket closed unexpectedly")
        buf += chunk
    return buf[:count], buf[count:]


def _ws_recv_message(sock: ssl.SSLSocket, leftover: bytes = b"") -> tuple[bytes, bytes]:
    pieces: list[bytes] = []
    while True:
        header, leftover = _ws_recv_exact(sock, leftover, 2)
        fin = header[0] & 0x80
        opcode = header[0] & 0x0F
        masked = header[1] & 0x80
        length = header[1] & 0x7F
        if length == 126:
            extra, leftover = _ws_recv_exact(sock, leftover, 2)
            length = struct.unpack("!H", extra)[0]
        elif length == 127:
            extra, leftover = _ws_recv_exact(sock, leftover, 8)
            length = struct.unpack("!Q", extra)[0]
        mask = b""
        if masked:
            mask, leftover = _ws_recv_exact(sock, leftover, 4)
        payload, leftover = _ws_recv_exact(sock, leftover, length)
        if masked:
            payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        if opcode == 0x8:
            raise RuntimeError("Search WebSocket closed by server")
        if opcode == 0x9:
            sock.sendall(b"\x8A" + bytes([0x80 | len(payload)]) + _ws_mask(payload))
            continue
        if opcode in (0x0, 0x1, 0x2):
            pieces.append(payload)
            if fin:
                return b"".join(pieces), leftover
        raise RuntimeError(f"Unexpected Search WebSocket opcode {opcode}")


def search_tags_ws(query: str, *, offset: int = 0, limit: int = 24) -> list[dict[str, Any]]:
    query = (query or "").strip()
    if not query:
        return []

    raw = socket.create_connection((API_SEARCH_HOST, 443), timeout=20)
    context = ssl.create_default_context()
    sock = context.wrap_socket(raw, server_hostname=API_SEARCH_HOST)
    sock.settimeout(20)
    try:
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        handshake = (
            "GET / HTTP/1.1\r\n"
            f"Host: {API_SEARCH_HOST}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            f"Origin: {SITE_URL}\r\n"
            f"User-Agent: {USER_AGENT}\r\n"
            "\r\n"
        )
        sock.sendall(handshake.encode("ascii"))
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = sock.recv(4096)
            if not chunk:
                raise RuntimeError("Search WebSocket handshake failed")
            buf += chunk
        status_line = buf.split(b"\r\n", 1)[0].decode("ascii", "replace")
        if b" 101 " not in buf.split(b"\r\n", 1)[0]:
            raise RuntimeError(f"Search WebSocket handshake returned {status_line}")
        leftover = buf.split(b"\r\n\r\n", 1)[1]
        payload = {
            "type": "search",
            "ignore_stats": True,
            "payload": {
                "Search_string": query,
                "offset": max(offset, 0),
                "limit": max(limit, 1),
                "category_id": None,
            },
        }
        _ws_send_text(sock, json.dumps(payload, separators=(",", ":")))
        data, _ = _ws_recv_message(sock, leftover)
        parsed = json.loads(data.decode("utf-8"))
        if not isinstance(parsed, list):
            return []
        tags: list[dict[str, Any]] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            slug = str(item.get("tg_slug") or "").strip()
            name = str(item.get("tg_name") or slug).strip()
            if not slug or not name:
                continue
            try:
                videos_count = int(item.get("tg_videos_count") or 0)
            except (TypeError, ValueError):
                videos_count = 0
            tags.append(
                {
                    "id": item.get("id"),
                    "name": name,
                    "slug": slug,
                    "kind": str(item.get("Tg_type") or "").strip(),
                    "videos_count": videos_count,
                }
            )
        return tags
    finally:
        try:
            sock.close()
        except OSError:
            pass


def pick_search_tag(tags: list[dict[str, Any]], query: str) -> dict[str, Any] | None:
    if not tags:
        return None
    query_lower = query.strip().lower()
    query_compact = re.sub(r"[^a-z0-9]", "", query_lower)
    exact: list[dict[str, Any]] = []
    for tag in tags:
        name_lower = tag["name"].lower()
        slug_lower = tag["slug"].lower()
        slug_compact = re.sub(r"[^a-z0-9]", "", slug_lower)
        if (
            query_lower == name_lower
            or query_lower == slug_lower
            or query_compact == slug_compact
        ):
            exact.append(tag)
    if exact:
        return max(exact, key=lambda item: item.get("videos_count", 0))
    return tags[0]


def _video_title(item: dict[str, Any]) -> str:
    file_data = item.get("file") if isinstance(item.get("file"), dict) else {}
    video_id = str(file_data.get("id") or "").strip()
    title = f"Video {video_id}" if video_id else "Video"
    for column in file_data.get("data") or []:
        if isinstance(column, dict) and column.get("cd_column") == "sf_name":
            title = str(column.get("cd_value") or title)
            break
    return title


def _thumbnail(item: dict[str, Any], video_id: str) -> str | None:
    facts = item.get("fc_facts")
    if not isinstance(facts, list) or not facts:
        return None
    first = facts[0] if isinstance(facts[0], dict) else {}
    thumbs = first.get("fc_thumbs")
    if not isinstance(thumbs, list) or not thumbs:
        return None
    offset = thumbs[0]
    return f"https://thumbs.externulls.com/videos/{video_id}/{offset}.webp"


def _parse_video(item: dict[str, Any]) -> dict[str, Any] | None:
    file_data = item.get("file") if isinstance(item.get("file"), dict) else {}
    video_id = str(file_data.get("id") or "").strip()
    if not video_id:
        return None
    duration = file_data.get("fl_duration")
    tags: list[str] = []
    for tag in item.get("tags") or []:
        if isinstance(tag, dict):
            name = str(tag.get("tg_name") or "").strip()
            if name:
                tags.append(re.sub(r"[{}]", "", name).strip())
    return {
        "video_id": video_id,
        "url": f"{SITE_URL}/{video_id}",
        "title": _video_title(item),
        "thumbnail": _thumbnail(item, video_id),
        "duration": duration,
        "tags": tags,
        "matched_tag": None,
    }


async def list_tag_videos(
    slug: str,
    *,
    max_count: int = 24,
    start_offset: int = 0,
) -> list[dict[str, Any]]:
    videos: list[dict[str, Any]] = []
    seen: set[str] = set()
    offset = max(start_offset, 0)
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0, headers=HTTP_HEADERS) as client:
        while len(videos) < max_count:
            url = API_TAG_SLUG.format(
                slug=quote(slug, safe=""),
                limit=PAGE_SIZE,
                offset=offset,
            )
            resp = await client.get(url)
            resp.raise_for_status()
            payload = resp.json()
            if not isinstance(payload, list) or not payload:
                break
            batch = 0
            for item in payload:
                if not isinstance(item, dict):
                    continue
                video = _parse_video(item)
                if not video or video["video_id"] in seen:
                    continue
                seen.add(video["video_id"])
                videos.append(video)
                batch += 1
                if len(videos) >= max_count:
                    break
            if len(payload) < PAGE_SIZE or batch == 0:
                break
            offset += PAGE_SIZE
    return videos


async def search_videos(query: str, *, max_count: int = 24) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Return (matched_tag, videos) for a keyword search."""
    tags = await asyncio.to_thread(search_tags_ws, query, offset=0, limit=24)
    tag = pick_search_tag(tags, query)
    if not tag:
        return None, []
    videos = await list_tag_videos(tag["slug"], max_count=max_count)
    for video in videos:
        video["matched_tag"] = tag["name"]
    return tag, videos


def looks_like_video_id(query: str) -> bool:
    raw = (query or "").strip()
    if not raw:
        return False
    if re.fullmatch(r"-?\d+", raw):
        return True
    lower = raw.lower()
    return "beeg.com" in lower or lower.startswith(("http://", "https://", "//", "beeg.com/"))
