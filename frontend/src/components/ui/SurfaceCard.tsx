import './ui.css'

interface Props {
  children: React.ReactNode
  className?: string
}

export function SurfaceCard({ children, className = '' }: Props) {
  return (
    <div className={`surface-card ${className}`.trim()}>
      {children}
    </div>
  )
}
