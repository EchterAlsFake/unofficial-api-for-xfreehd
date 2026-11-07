import { useCallback, useRef, useState } from "react";
import { searchStream } from "../../core/api";
import type { MediaItem, SearchParams } from "../../core/types";

export function useSearch() {
  const [results, setResults] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [doneCount, setDoneCount] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const search = useCallback((params: SearchParams) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setResults([]);
    setError(null);
    setDoneCount(null);
    setLoading(true);

    searchStream(
      params,
      {
        onItem: (item) => {
          setResults((prev) => {
            if (prev.some((v) => v.url === item.url && v.provider === item.provider)) {
              return prev;
            }
            return [...prev, item];
          });
        },
        onDone: (count) => {
          setDoneCount(count);
          setLoading(false);
        },
        onError: (message) => {
          setError(message);
          setLoading(false);
        },
      },
      controller.signal,
    );
  }, []);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    setLoading(false);
  }, []);

  return { results, loading, error, doneCount, search, cancel };
}
