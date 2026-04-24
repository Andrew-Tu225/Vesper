import { FetchError } from '@/types/api'

/**
 * Typed fetch wrapper. Always uses relative /api/... paths so the Vite proxy
 * can forward requests to the backend while preserving the vesper_session cookie.
 * Never pass absolute http://localhost:8000 URLs — they break cookie forwarding.
 */
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = path.startsWith('/api') ? path : `/api${path}`

  const response = await fetch(url, {
    ...init,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })

  if (!response.ok) {
    let message = `HTTP ${response.status}`
    try {
      const body = (await response.json()) as { detail?: string }
      message = body.detail ?? message
    } catch {
      // ignore parse errors
    }
    throw new FetchError(response.status, message)
  }

  const json = (await response.json()) as unknown
  if (
    json !== null &&
    typeof json === 'object' &&
    'success' in json &&
    'data' in json
  ) {
    const envelope = json as { success: boolean; data: unknown; error: string | null }
    if (!envelope.success) {
      throw new FetchError(response.status, envelope.error ?? 'Unknown error')
    }
    return envelope.data as T
  }
  return json as T
}

export function getParam(
  params: URLSearchParams,
  key: string,
  fallback: string = ''
): string {
  return params.get(key) ?? fallback
}
