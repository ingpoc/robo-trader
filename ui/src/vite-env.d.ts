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

interface AppRuntimeIdentity {
  runtime: 'frontend' | 'backend'
  git_sha: string | null
  git_short_sha: string | null
  build_id: string
  started_at: string
  workspace_path: string | null
}

declare const __APP_RUNTIME_IDENTITY__: AppRuntimeIdentity

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

interface WebMCPRegisteredTool {
  name: string
  description?: string
  inputSchema?: string | Record<string, unknown>
}

interface WebMCPModelContextTesting {
  listTools: () => Promise<WebMCPRegisteredTool[]>
  executeTool: (toolName: string, input: string) => Promise<unknown>
}

interface Navigator {
  modelContext?: WebMCPModelContext
  modelContextTesting?: WebMCPModelContextTesting
}
