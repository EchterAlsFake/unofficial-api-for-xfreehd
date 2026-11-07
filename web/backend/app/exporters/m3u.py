from __future__ import annotations

from app.exporters.base import PlaylistEntry

# VLC applies these to the item (and typically HLS follow-up requests).
_VLC_HEADER_MAP = {
    "User-Agent": "http-user-agent",
    "Referer": "http-referrer",
    "Origin": None,  # injected via http-extra-header below
}


def _escape(text: str) -> str:
    return text.replace("\n", " ").replace("\r", " ").strip()


class M3UExporter:
    id = "m3u"
    name = "M3U Playlist"
    description = "M3U for VLC / mpv — embeds HTTP headers when a CDN requires them"
    mime_type = "audio/x-mpegurl"
    extension = "m3u"

    def render(self, entries: list[PlaylistEntry]) -> str:
        lines = ["#EXTM3U"]
        for entry in entries:
            lines.append(f"#EXTINF:-1,{_escape(entry.title)}")
            headers = entry.http_headers or {}
            if headers.get("User-Agent"):
                lines.append(f"#EXTVLCOPT:http-user-agent={headers['User-Agent']}")
            if headers.get("Referer"):
                lines.append(f"#EXTVLCOPT:http-referrer={headers['Referer']}")
            # Extra headers (Origin, Accept, …) for picky CDNs like surrit.com
            for key, value in headers.items():
                if key in ("User-Agent", "Referer") or not value:
                    continue
                lines.append(f"#EXTVLCOPT:http-extra-header={key}: {value}")
            lines.append(entry.url)
        return "\n".join(lines) + "\n"
