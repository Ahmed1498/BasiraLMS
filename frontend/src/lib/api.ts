const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1').replace(/\/+$/, '')

let accessToken: string | null = null
let refreshRequest: Promise<string | null> | null = null

export function setAccessToken(token: string | null) {
  accessToken = token
}

function isPublicAuthEndpoint(endpoint: string) {
  return /^\/auth\/(register|signup|login|verify-email|confirm|forgot-password|reset-password|refresh|logout)(\/|$)/.test(endpoint)
}

async function refreshAccessToken(): Promise<string | null> {
  if (!refreshRequest) {
    refreshRequest = (async () => {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
      })
      if (response.status === 401) {
        accessToken = null
        return null
      }
      if (!response.ok) throw await responseError(response)
      const result = await response.json() as { access_token?: string }
      if (!result.access_token) {
        accessToken = null
        throw new Error('The authentication server returned an invalid refresh response.')
      }
      accessToken = result.access_token
      return accessToken
    })()
  }

  try {
    return await refreshRequest
  } finally {
    refreshRequest = null
  }
}

async function sendRequest(endpoint: string, options: RequestInit, token: string | null) {
  const headers = new Headers(options.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  return fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    credentials: 'include',
    headers,
  })
}

async function responseError(response: Response) {
  const responseText = await response.text()
  let message = `Request failed (${response.status})`
  if (responseText) {
    try {
      const errorData: unknown = JSON.parse(responseText)
      if (
        typeof errorData === 'object' &&
        errorData !== null &&
        'detail' in errorData &&
        typeof errorData.detail === 'string'
      ) {
        message = errorData.detail
      } else {
        message = responseText
      }
    } catch {
      message = responseText
    }
  }
  return new Error(message)
}

export async function apiFetch<T = unknown>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const publicAuthEndpoint = isPublicAuthEndpoint(endpoint)
  if (!accessToken && !publicAuthEndpoint) {
    accessToken = await refreshAccessToken()
    if (!accessToken) throw new Error('Your session has expired. Sign in again to continue.')
  }

  let response = await sendRequest(endpoint, options, accessToken)
  if (response.status === 401 && !publicAuthEndpoint) {
    accessToken = await refreshAccessToken()
    if (!accessToken) throw new Error('Your session has expired. Sign in again to continue.')
    response = await sendRequest(endpoint, options, accessToken)
  }

  if (!response.ok) throw await responseError(response)
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}
