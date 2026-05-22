const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8765'
let authToken: string | null = null

export function getBackendUrl(): string {
  return BACKEND_URL
}

export function getWsUrl(): string {
  return BACKEND_URL.replace('http://', 'ws://').replace('https://', 'wss://')
}

export function setAuthToken(token: string | null): void {
  authToken = token
}

export function getAuthToken(): string | null {
  return authToken
}

export async function fetchWithAuth(endpoint: string, options: RequestInit = {}): Promise<Response> {
  const url = `${BACKEND_URL}${endpoint}`
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  }
  
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`
  }
  
  const response = await fetch(url, {
    ...options,
    headers,
  })
  
  return response
}

export async function initAuth(): Promise<void> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/auth/token`)
    const data = await response.json()
    if (data.token) {
      authToken = data.token
    }
  } catch (error) {
    console.error('[API] Failed to get auth token:', error)
  }
}
