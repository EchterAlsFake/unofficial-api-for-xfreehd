import type { ExporterInfo, MediaItem, MetaResponse, ProviderInfo, SearchParams } from "./types";

export type SearchHandlers = {
  onItem: (item: MediaItem) => void;
  onDone: (count: number) => void;
  onError: (message: string) => void;
};

export async function fetchMeta(signal?: AbortSignal): Promise<MetaResponse> {
  const res = await fetch("/api/meta", { signal });
  if (!res.ok) throw new Error(`Meta request failed (${res.status})`);
  return res.json();
}

export function searchStream(
  params: SearchParams,
  handlers: SearchHandlers,
  signal?: AbortSignal,
): void {
  const qs = new URLSearchParams({
    q: params.q,
    provider: params.provider,
    stream: "true",
  });

  for (const [key, value] of Object.entries(params.filters)) {
    qs.set(key, String(value));
  }

  const source = new EventSource(`/api/search?${qs.toString()}`);
  let finished = false;

  const finish = () => {
    finished = true;
    source.close();
  };

  signal?.addEventListener("abort", () => finish(), { once: true });

  source.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data) as
        | { type: "item"; data: MediaItem }
        | { type: "done"; count: number }
        | { type: "error"; message: string };

      if (payload.type === "item") handlers.onItem(payload.data);
      else if (payload.type === "done") {
        handlers.onDone(payload.count);
        finish();
      } else if (payload.type === "error") {
        handlers.onError(payload.message);
        finish();
      }
    } catch (err) {
      handlers.onError(err instanceof Error ? err.message : "Invalid search payload");
      finish();
    }
  };

  source.onerror = () => {
    if (finished || signal?.aborted) {
      source.close();
      return;
    }
    handlers.onError("Search stream disconnected");
    finish();
  };
}

export async function fetchMedia(
  url: string,
  provider?: string,
  signal?: AbortSignal,
): Promise<MediaItem> {
  const qs = new URLSearchParams({ url });
  if (provider) qs.set("provider", provider);
  const res = await fetch(`/api/video?${qs.toString()}`, { signal });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Media request failed (${res.status})`);
  }
  return res.json();
}

export async function exportPlaylist(
  items: Array<{ url: string; title?: string | null; provider?: string }>,
  exporter: string,
  quality = "best",
): Promise<{ blob: Blob; exporter: ExporterInfo | { extension: string } }> {
  const res = await fetch("/api/playlist/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ items, exporter, quality, resolve: true }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Playlist export failed (${res.status})`);
  }
  return { blob: await res.blob(), exporter: { extension: exporter } };
}

export function downloadBlob(blob: Blob, filename: string) {
  const href = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = href;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(href);
}

export function defaultFilters(provider: ProviderInfo | undefined): Record<string, string | number> {
  const out: Record<string, string | number> = {};
  for (const field of provider?.filters ?? []) {
    if (field.default !== undefined && field.default !== null) {
      out[field.key] = field.default;
    }
  }
  return out;
}
