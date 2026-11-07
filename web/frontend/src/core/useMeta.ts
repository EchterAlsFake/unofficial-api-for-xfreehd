import { useEffect, useState } from "react";
import { fetchMeta } from "./api";
import type { MetaResponse } from "./types";

const EMPTY: MetaResponse = {
  providers: [],
  exporters: [],
  default_provider: null,
};

export function useMeta() {
  const [meta, setMeta] = useState<MetaResponse>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchMeta(controller.signal)
      .then(setMeta)
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setError(err instanceof Error ? err.message : "Meta laden mislukt");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  return { meta, loading, error };
}
