import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import type { FetchError } from '@/types/api'

export interface LinkedInStatus {
  connected: boolean
}

export function useLinkedInStatus() {
  return useQuery<LinkedInStatus, FetchError>({
    queryKey: ['linkedInStatus'],
    queryFn: () => apiFetch<LinkedInStatus>('/api/oauth/linkedin/status'),
    retry: false,
    throwOnError: false,
  })
}