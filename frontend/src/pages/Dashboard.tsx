import { useSearchParams } from 'react-router-dom'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import { SurfaceCard } from '@/components/ui/SurfaceCard'
import '@/components/ui/ui.css'

export default function Dashboard() {
  const { data: user } = useCurrentUser()
  const [params] = useSearchParams()
  const error = params.get('error')

  return (
    <div>
      {error && (
        <div className="error-banner" style={{ marginBottom: 'var(--space-6)' }}>
          Authentication error: {error}
        </div>
      )}
      <h1 style={{ marginBottom: 'var(--space-6)' }}>
        {user?.display_name ? `Welcome, ${user.display_name}` : 'Dashboard'}
      </h1>
      <SurfaceCard>
        <h3 style={{ marginBottom: 'var(--space-3)' }}>Getting started</h3>
        <p style={{ color: 'var(--color-text-muted)' }}>
          Connect Slack and LinkedIn to start turning internal signals into LinkedIn posts.
        </p>
      </SurfaceCard>
    </div>
  )
}
