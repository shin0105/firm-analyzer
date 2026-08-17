/**
 * Single source of truth for the backend address.
 *
 * Set VITE_API_BASE_URL in `frontend/.env` (or `.env.local`) to point at a
 * non-default backend. It falls back to the port `firm-app` listens on, so a
 * plain `npm run dev` against a local backend needs no configuration.
 */
export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8001';

/** Build an absolute backend URL from a root-relative path. */
export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
}

/** One category as returned by /api/results/summary. */
export interface Category {
  id: string;
  name: string;
  count: number;
  color?: string;
}

/** One firm as returned by /api/results/<category_id>. */
export interface Firm {
  name: string;
  summary: string;
}

/** Response shape of /api/upload-pdf. */
export interface UploadResult {
  success: boolean;
  message?: string;
  output_file?: string;
  error?: string;
}

/**
 * Application config, as stored in config.yml.
 *
 * Only the fields the UI actually edits are named. The index signature keeps
 * the rest of the document intact on round-trip, so saving from this form
 * never drops keys the UI does not know about.
 */
export interface AppConfig {
  summary?: {
    language?: string;
    output_format?: string;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}
