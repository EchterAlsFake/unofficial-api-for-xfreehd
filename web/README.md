# Media Browser GUI

React frontend + modular FastAPI bridge around `xfreehd_api`.

## Architecture

```
web/backend/app/
  providers/          # MediaProvider plugins (xfreehd today, more later)
  exporters/          # Playlist exporters (m3u today)
  routers/            # Thin HTTP adapters
  schemas.py          # Shared DTOs (MediaItem, filters, …)
  factory.py          # create_app() wires registries

web/frontend/src/
  core/               # types, API client, meta hook
  modules/
    search/           # SearchBar + SSE search hook
    video/            # cards + detail modal
    playlist/         # selection + export bar
```

### Built-in providers

| id | Package | Notes |
|---|---|---|
| `xfreehd` | this repo | RAW/CDN streams |
| `missav` | [`unofficial-api-for-missav`](https://github.com/EchterAlsFake/unofficial-api-for-missav) | HLS / m3u8 (via lokale proxy) |
| `xnxx` | [`unofficial-api-for-xnxx`](https://github.com/EchterAlsFake/unofficial-api-for-xnxx) | HLS / m3u8 |
| `beeg` | [`unofficial-api-for-beeg`](https://github.com/EchterAlsFake/unofficial-api-for-beeg) + externulls WS search | Keyword → tag → videos (max 100); URL/ID lookup also works |

The UI shows a **Bron** selector when more than one provider is registered.

### Add a new provider (backend)

1. Implement `MediaProvider` (see `app/providers/_example_stub.py`)
2. Register in `build_default_registry()`
3. Done — `/api/meta` and `/api/search?provider=…` pick it up; the UI renders filters dynamically

### Add a new exporter

1. Implement `PlaylistExporter` (`render(entries) -> str`)
2. Register in `build_default_exporters()`
3. UI shows it in the playlist bar automatically

## Start

Terminal 1 — API (from `web/backend`, using the repo venv):

```bash
uv sync --group gui --group dev
cd web/backend
../../.venv/Scripts/python -m uvicorn main:app --reload --host 127.0.0.1 --port 8787
```

Windows PowerShell:

```powershell
cd web\backend
..\..\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8787
```

Terminal 2 — UI:

```bash
cd web/frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173

## API sketch

| Endpoint | Role |
|---|---|
| `GET /api/meta` | Providers + filters + exporters |
| `GET /api/search?q=&provider=&stream=true` | SSE search |
| `GET /api/video?url=&provider=` | Detail |
| `POST /api/playlist/export` | Resolve streams → M3U (or other exporter) |
