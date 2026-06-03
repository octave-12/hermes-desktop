const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8765'
let authToken: string | null = null

export function getBackendUrl(): string {
  return BACKEND_URL
}

export function getWsUrl(): string {
  const wsUrl = BACKEND_URL.replace('http://', 'ws://').replace('https://', 'wss://')
  return wsUrl.endsWith('/ws') ? wsUrl : `${wsUrl}/ws`
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
      console.log('[API] Auth token initialized')
    }
  } catch (error) {
    // Auth is optional for Electron desktop app
    console.log('[API] Auth not available, continuing without auth')
  }
}
