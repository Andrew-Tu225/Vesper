import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchSignals,
  fetchSignal,
  approveSignal,
  rejectSignal,
  rewriteSignal,
} from '@/lib/signals'

export function useSignals(statusFilter?: string) {
  return useQuery({
    queryKey: ['signals', statusFilter ?? 'all'],
    queryFn: () => fetchSignals(statusFilter),
  })
}

export function useSignal(id: string, enabled = true) {
  return useQuery({
    queryKey: ['signal', id],
    queryFn: () => fetchSignal(id),
    enabled,
  })
}

export function useApprove() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      variant_number,
      scheduled_at,
      body_override,
    }: {
      id: string
      variant_number: number
      scheduled_at: string
      body_override?: string
    }) => approveSignal(id, { variant_number, scheduled_at, ...(body_override !== undefined && { body_override }) }),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: ['signals'] })
      qc.invalidateQueries({ queryKey: ['signal', id] })
    },
  })
}

export function useReject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id }: { id: string }) => rejectSignal(id),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: ['signals'] })
      qc.invalidateQueries({ queryKey: ['signal', id] })
    },
  })
}

export function useRewrite() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      variant_number,
      feedback,
    }: {
      id: string
      variant_number: number
      feedback: string
    }) => rewriteSignal(id, { variant_number, feedback }),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: ['signals'] })
      qc.invalidateQueries({ queryKey: ['signal', id] })
    },
  })
}
