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

interface WebMCPToolDefinition {
  name: string
  description: string
  inputSchema: Record<string, unknown>
  execute: (input?: Record<string, unknown>) => unknown | Promise<unknown>
}

interface WebMCPRegistrationOptions {
  signal?: AbortSignal
}

interface WebMCPModelContext {
  registerTool: (tool: WebMCPToolDefinition, options?: WebMCPRegistrationOptions) => void
}

interface Navigator {
  modelContext?: WebMCPModelContext
}
