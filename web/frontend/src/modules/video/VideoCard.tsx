import type { MediaItem } from "../../core/types";

type Props = {
  item: MediaItem;
  selected: boolean;
  index: number;
  onToggle: (item: MediaItem) => void;
  onOpen: (item: MediaItem) => void;
};

export function VideoCard({ item, selected, index, onToggle, onOpen }: Props) {
  const title = item.title || item.id || "Untitled";

  return (
    <article
      className={`video-card ${selected ? "is-selected" : ""}`}
      style={{ animationDelay: `${Math.min(index, 24) * 35}ms` }}
    >
      <div className="thumb-wrap">
        <button
          type="button"
          className={`check-btn ${selected ? "is-on" : ""}`}
          aria-pressed={selected}
          aria-label={selected ? "Deselecteer voor M3U" : "Selecteer voor M3U"}
          onClick={(e) => {
            e.stopPropagation();
            onToggle(item);
          }}
        >
          <span className="check-mark" aria-hidden>
            {selected ? "✓" : ""}
          </span>
        </button>

        <button type="button" className="thumb-btn" onClick={() => onOpen(item)}>
          {item.thumbnail ? (
            <img src={item.thumbnail} alt="" loading="lazy" />
          ) : (
            <div className="thumb-fallback" />
          )}
          {item.length ? <span className="badge duration">{item.length}</span> : null}
          {item.rating ? <span className="badge rating">{item.rating}</span> : null}
        </button>
      </div>

      <div className="card-body">
        <h3 title={title}>{title}</h3>
        <div className="meta">
          {item.views ? <span>{item.views}</span> : null}
          {item.author ? <span>{item.author}</span> : null}
          {item.provider ? <span className="provider-tag">{item.provider}</span> : null}
        </div>
        <label className="select-row">
          <input
            type="checkbox"
            checked={selected}
            onChange={() => onToggle(item)}
          />
          <span>Toevoegen aan M3U</span>
        </label>
      </div>
    </article>
  );
}
