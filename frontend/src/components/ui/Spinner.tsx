import './ui.css'

interface Props {
  size?: 'sm' | 'lg'
}

export function Spinner({ size }: Props) {
  return <div className={`spinner${size === 'lg' ? ' spinner--lg' : ''}`} aria-label="Loading" />
}
