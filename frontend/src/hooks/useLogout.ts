import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import { CURRENT_USER_KEY } from '@/hooks/useCurrentUser'

export function useLogout() {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: () => apiFetch('/api/auth/logout', { method: 'POST' }),
    onSettled: () => {
      qc.setQueryData(CURRENT_USER_KEY, null)
      qc.invalidateQueries({ queryKey: CURRENT_USER_KEY })
    },
  })
}
