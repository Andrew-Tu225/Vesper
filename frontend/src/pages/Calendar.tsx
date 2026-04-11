import { SurfaceCard } from '@/components/ui/SurfaceCard'

export default function Calendar() {
  return (
    <div>
      <h1 style={{ marginBottom: 'var(--space-6)' }}>Calendar</h1>
      <SurfaceCard>
        <p style={{ color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
          No scheduled posts yet.
        </p>
      </SurfaceCard>
    </div>
  )
}
