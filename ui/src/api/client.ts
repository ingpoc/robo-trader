const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export class APIError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    message: string
  ) {
    super(message)
    this.name = 'APIError'
  }
}

export async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`

  const config: RequestInit = {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  }

  try {
    const response = await fetch(url, config)

    if (!response.ok) {
      let errorMessage = `Request failed: ${response.statusText}`

      try {
        const errorData = await response.json()
        errorMessage = errorData.error || errorData.detail || errorMessage
      } catch {
        errorMessage = await response.text() || errorMessage
      }

      throw new APIError(response.status, response.statusText, errorMessage)
    }

    const data = await response.json()
    return data as T
  } catch (error) {
    if (error instanceof APIError) {
      throw error
    }

    throw new Error(
      error instanceof Error ? error.message : 'Network request failed'
    )
  }
}

export const api = {
  get: <T>(endpoint: string) => apiRequest<T>(endpoint, { method: 'GET' }),

  post: <T>(endpoint: string, data?: unknown) =>
    apiRequest<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    }),

  put: <T>(endpoint: string, data?: unknown) =>
    apiRequest<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    }),

  delete: <T>(endpoint: string) =>
    apiRequest<T>(endpoint, { method: 'DELETE' }),
}
