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

/** `segmentation.json` for a firm — see `taxonomy.yml` for the ids. */
export interface Segmentation {
  sector: string;
  subsector: string | null;
  verticals: string[];
  business_model: string;
  value_chain: string;
  profile: Record<string, string>;
  confidence: Record<string, string>;
  evidence: Record<string, string>;
  signals: string[];
}

export interface Firm {
  name: string;
  summary: string;
  /** Null until the firm is segmented (summarize or `firm-segment`). */
  segmentation?: Segmentation | null;
  path?: string;
}

/** `GET /api/results/:categoryId` */
export interface FirmsResponse {
  firms: Firm[];
  count: number;
}

/** One row of `GET /api/firms`: enough to list and filter, no full summary. */
export interface FirmListItem {
  name: string;
  category_id: string;
  category: string;
  address: string;
  segmented: boolean;
  sector: string | null;
  subsector: string | null;
  verticals: string[];
  business_model: string | null;
  sector_confidence: string | null;
  /** ~90 characters of summary prose, centred on the search term if any. */
  snippet: string;
}

/** Query parameters accepted by `GET /api/firms`; empty means "any". */
export interface FirmQuery {
  q?: string;
  category?: string;
  sector?: string;
  vertical?: string;
  business_model?: string;
  confidence?: string;
  segmented?: 'true' | 'false';
}

/** `GET /api/firms` */
export interface FirmListResponse {
  firms: FirmListItem[];
  count: number;
  /** Firms scanned before `q` and the filters (all of them, or one category's). */
  total: number;
}

/** `GET /api/firms/:categoryId/:firmName` */
export interface FirmDetail {
  name: string;
  category_id: string;
  category: string;
  address: string;
  summary: string;
  segmentation: Segmentation | null;
}

/** An id/label pair from `taxonomy.yml`. */
export interface TaxonomyEntry {
  id: string;
  name: string;
  name_en?: string;
  color?: string;
}

export interface TaxonomySector extends TaxonomyEntry {
  subsectors?: TaxonomyEntry[];
}

/** `GET /api/taxonomy` — the parts of `taxonomy.yml` the UI reads. */
export interface Taxonomy {
  sectors: TaxonomySector[];
  verticals: TaxonomyEntry[];
  business_models: TaxonomyEntry[];
  value_chain: TaxonomyEntry[];
  profile: Record<string, TaxonomyEntry[]>;
  confidence_levels?: string[];
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

/** What a background job runs: one script, or filter then summarize. */
export type JobKind = 'filter' | 'summarize' | 'segment' | 'pipeline';

export type JobStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled';

/** A pipeline run, as returned by `/api/jobs` (see `web/jobs.py`). Times are epoch seconds. */
export interface Job {
  id: string;
  kind: JobKind;
  options: Record<string, unknown>;
  status: JobStatus;
  /** Script names in run order; `step_index` points at the current one. */
  steps: string[];
  step_index: number;
  created_at: number;
  started_at: number | null;
  finished_at: number | null;
  /** Seconds run so far (or in total), computed by the server. */
  elapsed: number | null;
  returncode: number | null;
  error: string | null;
  /** From the `[i/n]` the scripts print per firm; null until the first one. */
  progress: { current: number; total: number } | null;
  /** The script's closing `Summary: …` line, once printed. */
  summary: string | null;
  log_lines: number;
}

/** `GET /api/jobs/:id?since=n` — the job plus log lines from index `log_start`. */
export interface JobWithLog extends Job {
  log: string[];
  log_start: number;
  /** Pass as `since` on the next poll. */
  log_next: number;
  /** Lines before `log_start` were dropped from the server's bounded buffer. */
  log_truncated: boolean;
}

/** `GET /api/jobs` */
export interface JobsResponse {
  jobs: Job[];
  active: string | null;
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
