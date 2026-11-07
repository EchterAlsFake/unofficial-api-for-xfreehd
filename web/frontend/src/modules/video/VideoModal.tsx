import { useEffect, useState } from "react";
import { fetchMedia } from "../../core/api";
import type { MediaItem } from "../../core/types";

type Props = {
  item: MediaItem | null;
  onClose: () => void;
};

export function VideoModal({ item, onClose }: Props) {
  const [detail, setDetail] = useState<MediaItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!item) {
      setDetail(null);
      setError(null);
      return;
    }

    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setDetail(item);

    fetchMedia(item.url, item.provider, controller.signal)
      .then((data) => setDetail(data))
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setError(err instanceof Error ? err.message : "Laden mislukt");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [item]);

  useEffect(() => {
    if (!item) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [item, onClose]);

  if (!item) return null;

  const data = detail || item;
  const streams = data.stream_urls ?? [];
  const stream = streams[streams.length - 1];

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={data.title || "Video details"}
        onClick={(e) => e.stopPropagation()}
      >
        <button type="button" className="modal-close" onClick={onClose} aria-label="Sluiten">
          ×
        </button>

        <div className="modal-media">
          {stream ? (
            <video controls poster={data.thumbnail || undefined} src={stream} />
          ) : data.thumbnail ? (
            <img src={data.thumbnail} alt="" />
          ) : (
            <div className="thumb-fallback large" />
          )}
          {loading ? <div className="modal-loading">Details laden…</div> : null}
        </div>

        <div className="modal-body">
          <h2>{data.title || data.id || "Untitled"}</h2>
          <div className="meta">
            {data.length ? <span>{data.length}</span> : null}
            {data.views ? <span>{data.views} views</span> : null}
            {data.rating ? <span>{data.rating}</span> : null}
            {data.author ? <span>{data.author}</span> : null}
            {data.publish_date ? <span>{data.publish_date}</span> : null}
            {data.provider ? <span>{data.provider}</span> : null}
          </div>

          {error ? <p className="error-text">{error}</p> : null}

          {data.categories && data.categories.length > 0 ? (
            <div className="chip-row">
              {data.categories.map((c) => (
                <span key={c} className="chip">
                  {c}
                </span>
              ))}
            </div>
          ) : null}

          {data.tags && data.tags.length > 0 ? (
            <div className="chip-row muted">
              {data.tags.map((t) => (
                <span key={t} className="chip">
                  {t}
                </span>
              ))}
            </div>
          ) : null}

          <div className="modal-actions">
            <a className="btn btn-ghost" href={data.url} target="_blank" rel="noreferrer">
              Open bron
            </a>
            {stream ? (
              <a className="btn btn-primary" href={stream} target="_blank" rel="noreferrer">
                Directe stream
              </a>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
