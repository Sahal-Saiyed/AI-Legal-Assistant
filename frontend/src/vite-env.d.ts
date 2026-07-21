/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_LOGO_PATH?: string;
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
