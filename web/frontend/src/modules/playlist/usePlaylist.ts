import { useCallback, useEffect, useMemo, useState } from "react";
import { downloadBlob, exportPlaylist } from "../../core/api";
import type { ExporterInfo, MediaItem } from "../../core/types";

function keyOf(item: MediaItem) {
  return `${item.provider}:${item.url}`;
}

export function usePlaylist(exporters: ExporterInfo[]) {
  const [selected, setSelected] = useState<Record<string, MediaItem>>({});
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exporterId, setExporterId] = useState(exporters[0]?.id ?? "m3u");

  useEffect(() => {
    if (!exporters.length) return;
    if (!exporters.some((e) => e.id === exporterId)) {
      setExporterId(exporters[0].id);
    }
  }, [exporters, exporterId]);

  const selectedList = useMemo(() => Object.values(selected), [selected]);
  const activeExporter = exporters.find((e) => e.id === exporterId) ?? exporters[0];

  const toggle = useCallback((item: MediaItem) => {
    setSelected((prev) => {
      const next = { ...prev };
      const key = keyOf(item);
      if (next[key]) delete next[key];
      else next[key] = item;
      return next;
    });
  }, []);

  const isSelected = useCallback(
    (item: MediaItem) => Boolean(selected[keyOf(item)]),
    [selected],
  );

  const selectMany = useCallback((items: MediaItem[]) => {
    setSelected((prev) => {
      const next = { ...prev };
      for (const item of items) next[keyOf(item)] = item;
      return next;
    });
  }, []);

  const clear = useCallback(() => setSelected({}), []);

  const runExport = useCallback(async () => {
    if (selectedList.length === 0) return;
    const exporter = activeExporter ?? { id: "m3u", extension: "m3u" };
    setExporting(true);
    setError(null);
    try {
      const { blob } = await exportPlaylist(
        selectedList.map((v) => ({
          url: v.url,
          title: v.title,
          provider: v.provider,
        })),
        exporter.id,
      );
      downloadBlob(blob, `playlist.${exporter.extension}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export mislukt");
    } finally {
      setExporting(false);
    }
  }, [selectedList, activeExporter]);

  return {
    selectedList,
    count: selectedList.length,
    exporting,
    error,
    exporterId: activeExporter?.id ?? exporterId,
    setExporterId,
    toggle,
    selectMany,
    isSelected,
    clear,
    runExport,
  };
}
