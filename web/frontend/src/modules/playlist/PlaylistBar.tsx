import type { ExporterInfo } from "../../core/types";

type Props = {
  count: number;
  exporters: ExporterInfo[];
  exporterId: string;
  exporting: boolean;
  onExporterChange: (id: string) => void;
  onExport: () => void;
  onClear: () => void;
};

export function PlaylistBar({
  count,
  exporters,
  exporterId,
  exporting,
  onExporterChange,
  onExport,
  onClear,
}: Props) {
  if (count === 0) return null;

  const label =
    exporters.find((e) => e.id === exporterId)?.extension?.toUpperCase() ?? "M3U";

  return (
    <div className="playlist-bar" role="region" aria-label="Playlist export">
      <div className="playlist-info">
        <strong>{count}</strong> geselecteerd voor playlist
        {exporters.length > 1 ? (
          <select
            className="exporter-select"
            value={exporterId}
            onChange={(e) => onExporterChange(e.target.value)}
            disabled={exporting}
            aria-label="Exportformaat"
          >
            {exporters.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name}
              </option>
            ))}
          </select>
        ) : null}
      </div>
      <div className="playlist-actions">
        <button type="button" className="btn btn-ghost" onClick={onClear} disabled={exporting}>
          Wissen
        </button>
        <button
          type="button"
          className="btn btn-primary"
          onClick={onExport}
          disabled={exporting}
        >
          {exporting ? "Bezig met exporteren…" : `Download ${label}`}
        </button>
      </div>
    </div>
  );
}
