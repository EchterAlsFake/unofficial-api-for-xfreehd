export type FilterOption = {
  value: string;
  label: string;
};

export type FilterField = {
  key: string;
  label: string;
  type: "select" | "number" | "text" | string;
  default?: string | number | null;
  options?: FilterOption[];
  min?: number | null;
  max?: number | null;
};

export type MediaItem = {
  provider: string;
  url: string;
  id?: string | null;
  title?: string | null;
  thumbnail?: string | null;
  length?: string | null;
  views?: string | null;
  rating?: string | null;
  author?: string | null;
  publish_date?: string | null;
  tags?: string[];
  categories?: string[];
  stream_urls?: string[];
  embed_url?: string | null;
  is_private?: boolean | null;
  extras?: Record<string, unknown>;
};

export type ProviderInfo = {
  id: string;
  name: string;
  description: string;
  capabilities: string[];
  filters: FilterField[];
};

export type ExporterInfo = {
  id: string;
  name: string;
  description: string;
  mime_type: string;
  extension: string;
};

export type MetaResponse = {
  providers: ProviderInfo[];
  exporters: ExporterInfo[];
  default_provider: string | null;
};

export type SearchParams = {
  q: string;
  provider: string;
  filters: Record<string, string | number>;
};

/** @deprecated use MediaItem */
export type VideoSummary = MediaItem;
