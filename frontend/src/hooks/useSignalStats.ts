import { useQuery } from '@tanstack/react-query'
import { fetchSignalStats } from '@/lib/signals'
import type { FetchError, SignalStats } from '@/types/api'

export function useSignalStats() {
  return useQuery<SignalStats, FetchError>({
    queryKey: ['signalStats'],
    queryFn: fetchSignalStats,
    retry: false,
    throwOnError: false,
  })
}