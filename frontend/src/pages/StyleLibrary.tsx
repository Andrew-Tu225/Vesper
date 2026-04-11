import { SurfaceCard } from '@/components/ui/SurfaceCard'

export default function StyleLibrary() {
  return (
    <div>
      <h1 style={{ marginBottom: 'var(--space-6)' }}>Style Library</h1>
      <SurfaceCard>
        <h3 style={{ marginBottom: 'var(--space-3)' }}>No seed posts yet</h3>
        <p style={{ color: 'var(--color-text-muted)' }}>
          Add at least 5 approved LinkedIn posts to seed your brand voice.
        </p>
      </SurfaceCard>
    </div>
  )
}
