import { apiFetch } from '@/lib/api'
import type { SignalListResponse, SignalDetail } from '@/types/api'

export function fetchSignals(statusFilter?: string, page = 1, limit = 20): Promise<SignalListResponse> {
  const params = new URLSearchParams({ page: String(page), limit: String(limit) })
  if (statusFilter) params.set('status', statusFilter)
  return apiFetch<SignalListResponse>(`/api/signals?${params}`)
}

export function fetchSignal(id: string): Promise<SignalDetail> {
  return apiFetch<SignalDetail>(`/api/signals/${id}`)
}

export function approveSignal(
  id: string,
  payload: { variant_number: number; scheduled_at: string; body_override?: string }
): Promise<void> {
  return apiFetch(`/api/signals/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function rejectSignal(id: string): Promise<void> {
  return apiFetch(`/api/signals/${id}/reject`, { method: 'POST' })
}

export function rewriteSignal(
  id: string,
  payload: { variant_number: number; feedback: string }
): Promise<void> {
  return apiFetch(`/api/signals/${id}/rewrite`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
