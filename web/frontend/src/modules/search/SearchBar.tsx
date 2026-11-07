import { useEffect, useMemo, useState, type FormEvent } from "react";
import { defaultFilters } from "../../core/api";
import type { ProviderInfo, SearchParams } from "../../core/types";

type Props = {
  providers: ProviderInfo[];
  defaultProviderId: string | null;
  loading: boolean;
  onSearch: (params: SearchParams) => void;
  onCancel: () => void;
};

export function SearchBar({
  providers,
  defaultProviderId,
  loading,
  onSearch,
  onCancel,
}: Props) {
  const [q, setQ] = useState("");
  const [providerId, setProviderId] = useState(defaultProviderId ?? providers[0]?.id ?? "");
  const provider = useMemo(
    () => providers.find((p) => p.id === providerId) ?? providers[0],
    [providers, providerId],
  );
  const [filters, setFilters] = useState<Record<string, string | number>>(
    () => defaultFilters(provider),
  );

  useEffect(() => {
    setFilters(defaultFilters(provider));
  }, [provider]);

  useEffect(() => {
    if (!providerId && defaultProviderId) setProviderId(defaultProviderId);
  }, [defaultProviderId, providerId]);

  function submit(e: FormEvent) {
    e.preventDefault();
    const query = q.trim();
    if (!query || !provider) return;
    onSearch({ q: query, provider: provider.id, filters });
  }

  return (
    <form className="search-bar" onSubmit={submit}>
      <div className="search-main">
        <label className="sr-only" htmlFor="q">
          Zoeken
        </label>
        <input
          id="q"
          className="search-input"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={
            provider?.id === "beeg"
              ? "Zoek tag/studio of plak Beeg URL/ID…"
              : "Zoek video’s…"
          }
          autoComplete="off"
          spellCheck={false}
        />
        {loading ? (
          <button type="button" className="btn btn-ghost" onClick={onCancel}>
            Stop
          </button>
        ) : (
          <button type="submit" className="btn btn-primary" disabled={!q.trim()}>
            Zoeken
          </button>
        )}
      </div>

      <div className="search-filters">
        {providers.length > 1 ? (
          <label>
            <span>Bron</span>
            <select value={provider?.id ?? ""} onChange={(e) => setProviderId(e.target.value)}>
              {providers.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
        ) : null}

        {(provider?.filters ?? []).map((field) => (
          <label key={field.key}>
            <span>{field.label}</span>
            {field.type === "select" ? (
              <select
                value={String(filters[field.key] ?? field.default ?? "")}
                onChange={(e) =>
                  setFilters((prev) => ({ ...prev, [field.key]: e.target.value }))
                }
              >
                {(field.options ?? []).map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            ) : field.type === "number" ? (
              <select
                value={String(filters[field.key] ?? field.default ?? 1)}
                onChange={(e) =>
                  setFilters((prev) => ({ ...prev, [field.key]: Number(e.target.value) }))
                }
              >
                {Array.from(
                  { length: (field.max ?? 5) - (field.min ?? 1) + 1 },
                  (_, i) => (field.min ?? 1) + i,
                ).map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            ) : (
              <input
                value={String(filters[field.key] ?? "")}
                onChange={(e) =>
                  setFilters((prev) => ({ ...prev, [field.key]: e.target.value }))
                }
              />
            )}
          </label>
        ))}
      </div>
    </form>
  );
}
