import axios from 'axios';

/**
 * Base URL of the Flask backend. Empty means same origin: Flask serves the
 * production build, and the Vite dev server proxies `/api` to Flask. Set
 * `VITE_API_BASE` only when the API lives on another origin.
 */
export const API_BASE = (import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '');

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 30_000,
});

/** Absolute URL for a backend path, for iframes and download links. */
export function apiUrl(path: string): string {
  return `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`;
}

/**
 * Turn any thrown value into a message worth showing a user. Network failures
 * are the common case here (the backend simply isn't running), and axios
 * reports those as a bare "Network Error".
 */
export function errorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const payload = err.response?.data as { error?: string; message?: string } | undefined;
    if (payload?.error) return payload.error;
    if (payload?.message) return payload.message;
    if (err.code === 'ECONNABORTED') {
      return '서버 응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.';
    }
    if (!err.response) {
      return `서버에 연결할 수 없습니다 (${API_BASE || window.location.origin}). 백엔드가 실행 중인지 확인해 주세요.`;
    }
    return `서버 오류가 발생했습니다 (HTTP ${err.response.status}).`;
  }
  if (err instanceof Error) return err.message;
  return '알 수 없는 오류가 발생했습니다.';
}
