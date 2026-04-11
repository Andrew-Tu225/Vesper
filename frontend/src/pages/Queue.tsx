import { SurfaceCard } from '@/components/ui/SurfaceCard'

export default function Queue() {
  return (
    <div>
      <h1 style={{ marginBottom: 'var(--space-6)' }}>Queue</h1>
      <SurfaceCard>
        <p style={{ color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
          No content signals yet. Connect Slack to start capturing content.
        </p>
      </SurfaceCard>
    </div>
  )
}
