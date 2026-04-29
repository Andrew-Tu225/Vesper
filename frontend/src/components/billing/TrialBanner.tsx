import { useState } from 'react'
import { apiFetch } from '@/lib/api'
import { useBillingStatus } from '@/hooks/useBillingStatus'
import './billing.css'

function XIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <path d="M2 2l8 8M10 2L2 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}

export function TrialBanner() {
  const { data: billing } = useBillingStatus()
  const [dismissed, setDismissed] = useState(false)
  const [loading, setLoading] = useState(false)

  if (!billing?.isTrialing || dismissed) return null

  const days = billing.daysRemaining ?? 0
  const urgent = days <= 7
  const daysText =
    days === 0
      ? 'Your trial expires today'
      : `${days} day${days !== 1 ? 's' : ''} left in your trial`

  async function handleUpgrade() {
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

  return (
    <div className={`trial-banner${urgent ? ' trial-banner--urgent' : ''}`} role="status">
      <p className="trial-banner__text">{daysText}</p>
      <button className="trial-banner__cta" onClick={handleUpgrade} disabled={loading}>
        {loading ? 'Loading…' : 'Upgrade →'}
      </button>
      <button
        className="trial-banner__dismiss"
        onClick={() => setDismissed(true)}
        aria-label="Dismiss trial banner"
      >
        <XIcon />
      </button>
    </div>
  )
}