import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import type { FetchError } from '@/types/api'

interface BillingStatusResponse {
  subscription_status: string
  trial_ends_at: string | null
  days_remaining: number | null
  stripe_customer_id: string | null
  stripe_publishable_key: string
}

export interface BillingStatus {
  subscriptionStatus: string
  trialEndsAt: string | null
  daysRemaining: number | null
  isTrialing: boolean
  isActive: boolean
  isCancelled: boolean
  isSuspended: boolean
}

export function useBillingStatus() {
  return useQuery<BillingStatus, FetchError>({
    queryKey: ['billingStatus'],
    queryFn: async () => {
      const raw = await apiFetch<BillingStatusResponse>('/api/billing/status')
      return {
        subscriptionStatus: raw.subscription_status,
        trialEndsAt: raw.trial_ends_at,
        daysRemaining: raw.days_remaining,
        isTrialing: raw.subscription_status === 'trialing',
        isActive: raw.subscription_status === 'active',
        isCancelled: raw.subscription_status === 'cancelled',
        isSuspended: raw.subscription_status === 'suspended',
      }
    },
    staleTime: 60_000,
    retry: false,
    throwOnError: false,
  })
}