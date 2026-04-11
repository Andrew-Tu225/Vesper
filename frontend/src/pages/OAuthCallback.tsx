import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { CURRENT_USER_KEY } from '@/hooks/useCurrentUser'
import { ROUTES } from '@/lib/constants'
import { Spinner } from '@/components/ui/Spinner'
import '@/components/ui/ui.css'

/**
 * Generic /auth/callback page — safety net for OAuth flows that land here.
 * Currently Google redirects directly to /dashboard (cookie already set).
 * This page handles any future provider that uses query-param tokens,
 * or redirects here explicitly.
 */
export default function OAuthCallback() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const error = params.get('error')

  useEffect(() => {
    if (error) return

    // Cookie is already set by the backend before redirecting here.
    // Invalidate so RequireAuth refetches /me with the new session.
    qc.invalidateQueries({ queryKey: CURRENT_USER_KEY })
    navigate(ROUTES.DASHBOARD, { replace: true })
  }, [error, navigate, qc])

  if (error) {
    return (
      <div
        style={{
          minHeight: '100dvh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 'var(--space-4)',
          padding: 'var(--space-8)',
          textAlign: 'center',
        }}
      >
        <div className="error-banner" style={{ maxWidth: '400px', width: '100%' }}>
          Authentication failed: {error}
        </div>
        <a href={ROUTES.LOGIN} className="btn btn--secondary">
          Back to Login
        </a>
      </div>
    )
  }

  return (
    <div className="full-loading">
      <Spinner size="lg" />
    </div>
  )
}
