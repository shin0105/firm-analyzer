import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The Flask API (`uv run firm-app`). During `npm run dev` these paths are
// forwarded to it, so the browser only ever talks to one origin. A production
// build (`npm run build`) is served by Flask itself at http://localhost:8001.
const backend = process.env.VITE_BACKEND_URL ?? 'http://127.0.0.1:8001';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': backend,
      '/map': backend,
      '/static': backend,
    },
  },
});
