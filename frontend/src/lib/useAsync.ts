import { useCallback, useEffect, useRef, useState } from 'react';
import { errorMessage } from './api';

export type AsyncStatus = 'loading' | 'success' | 'error';

export interface AsyncState<T> {
  status: AsyncStatus;
  data: T | null;
  error: string | null;
  /** Re-run the fetch, e.g. from a "retry" button. */
  reload: () => void;
}

interface Settled<T> {
  key: string;
  data: T | null;
  error: string | null;
}

/**
 * Runs an async fetch and exposes the loading / error / success states the UI
 * needs, so every page can show real feedback instead of a silent blank
 * screen. `deps` behaves like a `useEffect` dependency list.
 *
 * State is only written from the promise callbacks; the loading state is
 * derived by comparing the settled result's key against the current one, which
 * keeps stale results from a superseded request off the screen.
 */
export function useAsync<T>(fetcher: () => Promise<T>, deps: unknown[] = []): AsyncState<T> {
  const [nonce, setNonce] = useState(0);
  const [settled, setSettled] = useState<Settled<T> | null>(null);

  const key = `${nonce}:${JSON.stringify(deps)}`;

  // Keep the latest fetcher reachable without making it an effect dependency.
  // This effect is declared first so it commits before the fetch effect below.
  const fetcherRef = useRef(fetcher);
  useEffect(() => {
    fetcherRef.current = fetcher;
  });

  useEffect(() => {
    let cancelled = false;

    fetcherRef
      .current()
      .then((result) => {
        if (!cancelled) setSettled({ key, data: result, error: null });
      })
      .catch((err: unknown) => {
        if (!cancelled) setSettled({ key, data: null, error: errorMessage(err) });
      });

    return () => {
      cancelled = true;
    };
  }, [key]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  // Anything settled under a previous key belongs to a request we no longer care
  // about, so the hook reports "loading" again.
  const current = settled?.key === key ? settled : null;
  const status: AsyncStatus = !current ? 'loading' : current.error ? 'error' : 'success';

  return { status, data: current?.data ?? null, error: current?.error ?? null, reload };
}
