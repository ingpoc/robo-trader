import { execSync } from 'node:child_process'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

const apiProxyTarget = process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000'
const wsProxyTarget = process.env.VITE_WS_TARGET || process.env.VITE_WS_PROXY_TARGET || 'ws://127.0.0.1:8000'
const frontendStartedAt = new Date().toISOString()

function readGitSha() {
  try {
    return execSync('git rev-parse HEAD', {
      cwd: __dirname,
      stdio: ['ignore', 'pipe', 'ignore'],
    }).toString().trim() || null
  } catch {
    return null
  }
}

const frontendGitSha = readGitSha()
const frontendGitShortSha = frontendGitSha ? frontendGitSha.slice(0, 12) : null
const frontendRuntimeIdentity = {
  runtime: 'frontend',
  git_sha: frontendGitSha,
  git_short_sha: frontendGitShortSha,
  build_id: `frontend-${frontendGitShortSha || 'unknown'}-${frontendStartedAt}`,
  started_at: frontendStartedAt,
  workspace_path: path.resolve(__dirname, '..'),
}

export default defineConfig({
  plugins: [react()],
  define: {
    __APP_RUNTIME_IDENTITY__: JSON.stringify(frontendRuntimeIdentity),
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: apiProxyTarget,
        changeOrigin: true,
        secure: false,
      },
      '/ws': {
        target: wsProxyTarget,
        ws: true,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'build',
    sourcemap: true,
  },
})
