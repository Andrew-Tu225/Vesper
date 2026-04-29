import { useState } from 'react'
import { apiFetch } from '@/lib/api'
import { useBillingStatus } from '@/hooks/useBillingStatus'
import './billing.css'

export function UpgradeNotice() {
  const { data: billing } = useBillingStatus()
  const [loading, setLoading] = useState(false)

  if (!billing) return null
  if (billing.isActive) return null
  if (billing.isTrialing && (billing.daysRemaining === null || billing.daysRemaining > 0)) return null

  async function handleCheckout() {
    setLoading(true)
    try {
      const { checkout_url } = await apiFetch<{ checkout_url: string }>(
        '/api/billing/create-checkout-session',
        { method: 'POST' },
      )
      window.location.href = checkout_url
    } finally {
      setLoading(false)
    }
  }

  const message = billing.isSuspended
    ? 'Your last payment failed — resubscribe to keep Vesper working.'
    : billing.isCancelled
      ? 'Your subscription has been cancelled — resubscribe to keep Vesper working.'
      : 'Your trial has ended — upgrade to Pro to keep Vesper working.'

  const ctaLabel = billing.isSuspended || billing.isCancelled ? 'Resubscribe' : 'Upgrade to Pro'

  return (
    <div className="upgrade-notice">
      <p className="upgrade-notice__text">{message}</p>
      <button className="btn--billing-primary" onClick={handleCheckout} disabled={loading}>
        {loading ? 'Loading…' : ctaLabel}
      </button>
    </div>
  )
}