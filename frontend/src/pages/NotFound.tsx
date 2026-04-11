import { Link } from 'react-router-dom'
import { ROUTES } from '@/lib/constants'
import '@/components/ui/ui.css'

export default function NotFound() {
  return (
    <div
      style={{
        minHeight: '100dvh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 'var(--space-4)',
      }}
    >
      <h1 style={{ fontSize: 'var(--text-hero)', color: 'var(--color-border)' }}>404</h1>
      <p style={{ color: 'var(--color-text-muted)' }}>This page doesn't exist.</p>
      <Link to={ROUTES.DASHBOARD} className="btn btn--secondary">
        Go to Dashboard
      </Link>
    </div>
  )
}
