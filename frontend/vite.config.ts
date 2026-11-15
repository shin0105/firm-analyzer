import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// The Flask API (`uv run firm-app`). During `npm run dev` these paths are
// forwarded to it, so the browser only ever talks to one origin. A production
// build (`npm run build`) is served by Flask itself at http://localhost:8001.
// The static build (`npm run build:static`) needs no Flask: see vercel.json.
const backend = process.env.VITE_BACKEND_URL ?? 'http://127.0.0.1:8001';

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': backend,
      '/map': backend,
      '/static': backend,
    },
  },
  // `vite preview` reuses server.proxy unless told otherwise. The static
  // build's /map and /static are files in dist/, so nothing is forwarded.
  preview: mode === 'static' ? { proxy: {} } : undefined,
}));
