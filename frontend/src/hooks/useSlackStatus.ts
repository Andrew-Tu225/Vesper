import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import type { FetchError } from '@/types/api'

export interface SlackStatus {
  connected: boolean
  workspace_name?: string
  channels_configured?: boolean
  channel_count?: number
}

export function useSlackStatus() {
  return useQuery<SlackStatus, FetchError>({
    queryKey: ['slackStatus'],
    queryFn: () => apiFetch<SlackStatus>('/api/oauth/slack/status'),
    retry: false,
    throwOnError: false,
  })
}