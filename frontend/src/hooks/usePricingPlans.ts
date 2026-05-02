import { useQuery } from '@tanstack/react-query'

export interface Plan {
  id: string
  name: string
  unit_amount: number | null
  currency: string
  interval: string
  featured: boolean
  features: string[]
  description: string
}

interface PlansResponse {
  plans: Plan[]
}

function formatPrice(unit_amount: number | null, currency: string): string {
  if (unit_amount === null) return '—'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency.toUpperCase(),
    maximumFractionDigits: 0,
  }).format(unit_amount / 100)
}

export { formatPrice }

export function usePricingPlans() {
  return useQuery<PlansResponse>({
    queryKey: ['pricingPlans'],
    queryFn: async () => {
      const res = await fetch('/api/billing/plans')
      if (!res.ok) throw new Error('Failed to fetch plans')
      return res.json() as Promise<PlansResponse>
    },
    staleTime: 60_000,
    retry: 1,
  })
}