import { useSyncExternalStore } from 'react';

export type Theme = 'light' | 'dark';

/** Same key as the script in index.html and the map page, which read it before first paint. */
const STORAGE_KEY = 'firm-analyzer-theme';
/** The browser chrome colour: the top bar's card colour in each theme. */
const THEME_COLOR: Record<Theme, string> = { light: '#ffffff', dark: '#181c21' };

const listeners = new Set<() => void>();

function currentTheme(): Theme {
  return document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function setTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', THEME_COLOR[theme]);
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Storage blocked (private mode): the choice lasts until the page reloads.
  }
  listeners.forEach((listener) => listener());
}

/** The theme on `<html data-theme>`, re-rendering when `setTheme` changes it. */
export function useTheme(): Theme {
  return useSyncExternalStore(subscribe, currentTheme, () => 'light');
}
