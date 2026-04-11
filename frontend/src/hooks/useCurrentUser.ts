import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import { FetchError } from '@/types/api'
import type { User } from '@/types/user'

export const CURRENT_USER_KEY = ['currentUser'] as const

export function useCurrentUser() {
  return useQuery<User, FetchError>({
    queryKey: CURRENT_USER_KEY,
    queryFn: () => apiFetch<User>('/api/auth/me'),
    retry: false,
    throwOnError: false,
  })
}
