import { useEffect, useState } from 'react'
import { apiFetch } from '@/lib/api'
import { useBillingStatus } from '@/hooks/useBillingStatus'
import './billing.css'

const STATUS_LABELS: Record<string, string> = {
  trialing: 'Trial',
  active: 'Active',
  suspended: 'Payment failed',
  cancelled: 'Cancelled',
}

const STATUS_CLASS: Record<string, string> = {
  trialing: 'status-pill--trial',
  active: 'status-pill--active',
  suspended: 'status-pill--warn',
  cancelled: 'status-pill--error',
}

interface Notice {
  type: 'success' | 'info'
  message: string
}

export function BillingCard() {
  const { data: billing, isLoading } = useBillingStatus()
  const [loading, setLoading] = useState(false)
  const [notice, setNotice] = useState<Notice | null>(null)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const result = params.get('billing')
    if (result === 'success') {
      setNotice({ type: 'success', message: 'Subscription activated — welcome to Pro!' })
      params.delete('billing')
      const qs = params.toString()
      window.history.replaceState(null, '', window.location.pathname + (qs ? '?' + qs : ''))
    } else if (result === 'cancel') {
      setNotice({ type: 'info', message: "Checkout cancelled. You can upgrade whenever you're ready." })
      params.delete('billing')
      const qs = params.toString()
      window.history.replaceState(null, '', window.location.pathname + (qs ? '?' + qs : ''))
    }
  }, [])

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

  async function handlePortal() {
    setLoading(true)
    try {
      const { portal_url } = await apiFetch<{ portal_url: string }>(
        '/api/billing/create-portal-session',
        { method: 'POST' },
      )
      window.location.href = portal_url
    } finally {
      setLoading(false)
    }
  }

  const status = billing?.subscriptionStatus ?? 'trialing'
  const planName = billing?.isActive ? 'Pro' : 'Trial'

  return (
    <div className="billing-card">
      {notice && (
        <div className={`billing-notice billing-notice--${notice.type}`}>
          <span>{notice.message}</span>
          <button
            className="billing-notice__dismiss"
            onClick={() => setNotice(null)}
            aria-label="Dismiss"
          >
            ×
          </button>
        </div>
      )}

      <div className="billing-card__body">
        <div className="billing-card__info">
          {isLoading ? (
            <span className="skeleton skeleton--text" style={{ width: 120 }} />
          ) : (
            <p className="billing-card__plan">{planName}</p>
          )}
          {isLoading ? (
            <span className="skeleton skeleton--pill" style={{ width: 72, height: 22 }} />
          ) : (
            <span className={`status-pill ${STATUS_CLASS[status] ?? ''}`}>
              {STATUS_LABELS[status] ?? status}
            </span>
          )}
          {billing?.isTrialing && billing.daysRemaining !== null && (
            <p className="billing-card__meta">
              {billing.daysRemaining === 0
                ? 'Trial expires today'
                : `${billing.daysRemaining} day${billing.daysRemaining !== 1 ? 's' : ''} remaining`}
            </p>
          )}
        </div>

        <div className="billing-card__action">
          {isLoading && (
            <span className="skeleton skeleton--pill" style={{ width: 128, height: 36 }} />
          )}
          {!isLoading && billing?.isActive && (
            <button className="btn--billing" onClick={handlePortal} disabled={loading}>
              {loading ? 'Loading…' : 'Manage billing'}
            </button>
          )}
          {!isLoading && !billing?.isActive && (
            <button className="btn--billing-primary" onClick={handleCheckout} disabled={loading}>
              {loading
                ? 'Loading…'
                : billing?.isSuspended || billing?.isCancelled
                  ? 'Resubscribe'
                  : 'Upgrade to Pro'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}