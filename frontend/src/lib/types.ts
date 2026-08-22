/** Shapes returned by the Flask API (see `src/firm_analyzer/web/app.py`). */

export interface CategorySummary {
  id: string;
  name: string;
  count: number;
  color: string;
}

/** `GET /api/results/summary` — category id → summary, plus a `total` number. */
export type ResultsSummaryResponse = Record<
  string,
  { name: string; count: number; color?: string } | number
>;

export interface Firm {
  name: string;
  summary: string;
  path: string;
}

/** `GET /api/results/:categoryId` */
export interface FirmsResponse {
  firms: Firm[];
  count: number;
}

/** One LLM back end as returned by `GET /api/llm/providers`. */
export interface LLMProvider {
  id: string;
  label: string;
  /** True when the server has an API key for this provider. */
  configured: boolean;
  /** True when this is the provider `config.yml` currently selects. */
  active: boolean;
  model: string;
  parser_model: string;
  /** Env var that supplies the key, for the "missing key" hint. */
  key_env: string;
  supports_native_pdf: boolean;
  notes: string;
}

/** `GET /api/llm/providers` */
export interface ProvidersResponse {
  providers: LLMProvider[];
  active: string;
}

/** `GET /api/config` */
export interface AppConfig {
  app?: {
    llm_provider?: string;
    llm_models?: Record<string, string>;
    [key: string]: unknown;
  };
  segmentation?: {
    enabled?: boolean;
    [key: string]: unknown;
  };
  summary?: {
    language?: string;
    output_format?: string;
    custom_prompt?: string;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

/** `POST /api/upload-pdf` */
export interface OcrResult {
  success: boolean;
  message?: string;
  output_file?: string;
  error?: string;
}

/** Split a summary response into ordered categories and a total. */
export function parseResultsSummary(data: ResultsSummaryResponse): {
  categories: CategorySummary[];
  total: number;
} {
  const categories: CategorySummary[] = [];
  let total = 0;

  for (const [id, value] of Object.entries(data ?? {})) {
    if (id === 'total') {
      total = typeof value === 'number' ? value : 0;
      continue;
    }
    if (value && typeof value === 'object') {
      categories.push({
        id,
        name: value.name ?? id,
        count: value.count ?? 0,
        color: value.color ?? '#607D8B',
      });
    }
  }

  return { categories, total };
}
