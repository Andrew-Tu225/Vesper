import { SurfaceCard } from '@/components/ui/SurfaceCard'

export default function Settings() {
  return (
    <div>
      <h1 style={{ marginBottom: 'var(--space-6)' }}>Settings</h1>
      <SurfaceCard>
        <p style={{ color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
          Workspace settings coming soon.
        </p>
      </SurfaceCard>
    </div>
  )
}
