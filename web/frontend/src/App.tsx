import { useState } from "react";
import { useMeta } from "./core/useMeta";
import type { MediaItem } from "./core/types";
import { PlaylistBar, usePlaylist } from "./modules/playlist";
import { SearchBar, useSearch } from "./modules/search";
import { VideoCard, VideoModal } from "./modules/video";

export default function App() {
  const { meta, loading: metaLoading, error: metaError } = useMeta();
  const { results, loading, error, doneCount, search, cancel } = useSearch();
  const playlist = usePlaylist(meta.exporters);
  const [active, setActive] = useState<MediaItem | null>(null);

  const brand =
    meta.providers.length > 1
      ? "Media Browser"
      : (meta.providers[0]?.name ?? "Media Browser");

  return (
    <div className="app">
      <div className="ambient ambient-a" aria-hidden />
      <div className="ambient ambient-b" aria-hidden />

      <header className="hero">
        <p className="brand">{brand}</p>
        <h1>Browse & playlist</h1>
        <p className="lede">
          Zoek → vink resultaten aan → download een M3U-playlist voor VLC / mpv.
        </p>
        {metaLoading ? (
          <p className="pulse">API verbinden…</p>
        ) : (
          <SearchBar
            providers={meta.providers}
            defaultProviderId={meta.default_provider}
            loading={loading}
            onSearch={search}
            onCancel={cancel}
          />
        )}
      </header>

      <main className="main">
        <div className="status-row">
          <div className="status-left">
            {loading ? (
              <span className="pulse">Laden… {results.length} gevonden</span>
            ) : doneCount !== null ? (
              <span>
                Klaar — {doneCount} resultaat{doneCount === 1 ? "" : "en"}
              </span>
            ) : results.length === 0 ? (
              <span>Voer een zoekterm in om te beginnen</span>
            ) : (
              <span>{results.length} resultaten</span>
            )}
            {metaError ? <span className="error-text">{metaError}</span> : null}
            {error ? <span className="error-text">{error}</span> : null}
            {playlist.error ? <span className="error-text">{playlist.error}</span> : null}
          </div>
          {results.length > 0 ? (
            <div className="status-actions">
              <button
                type="button"
                className="btn btn-ghost btn-small"
                onClick={() => playlist.selectMany(results)}
              >
                Alles selecteren
              </button>
              {playlist.count > 0 ? (
                <button
                  type="button"
                  className="btn btn-ghost btn-small"
                  onClick={playlist.clear}
                >
                  Selectie wissen
                </button>
              ) : null}
            </div>
          ) : null}
        </div>

        <section className="grid" aria-live="polite">
          {results.map((item, index) => (
            <VideoCard
              key={`${item.provider}:${item.url}`}
              item={item}
              index={index}
              selected={playlist.isSelected(item)}
              onToggle={playlist.toggle}
              onOpen={setActive}
            />
          ))}
        </section>
      </main>

      <PlaylistBar
        count={playlist.count}
        exporters={meta.exporters}
        exporterId={playlist.exporterId}
        exporting={playlist.exporting}
        onExporterChange={playlist.setExporterId}
        onExport={playlist.runExport}
        onClear={playlist.clear}
      />

      <VideoModal item={active} onClose={() => setActive(null)} />
    </div>
  );
}
