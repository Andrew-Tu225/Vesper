import './queue.css'

const STATUS_LABELS: Record<string, string> = {
  in_review: 'In Review',
  scheduled: 'Scheduled',
  approved: 'Approved',
  posted: 'Posted',
  failed: 'Failed',
  detected: 'Detected',
  classified: 'Classified',
  enriched: 'Enriched',
}

interface Props {
  status: string
}

export function StatusBadge({ status }: Props) {
  const label = STATUS_LABELS[status] ?? status
  const cls = ['in_review', 'scheduled', 'approved', 'posted', 'failed'].includes(status)
    ? status
    : 'default'

  return (
    <span className={`status-badge status-badge--${cls}`}>
      <span className="status-badge__dot" />
      {label}
    </span>
  )
}
