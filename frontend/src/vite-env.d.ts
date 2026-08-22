/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the Flask backend; see `.env.example`. */
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
