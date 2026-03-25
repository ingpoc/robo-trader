/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_WS_URL?: string
  readonly VITE_API_URL?: string
  readonly VITE_API_BASE_URL?: string
  readonly VITE_PROXY_TARGET?: string
  readonly VITE_WS_TARGET?: string
  readonly VITE_WS_PROXY_TARGET?: string
  // Add other env variables here as needed
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
