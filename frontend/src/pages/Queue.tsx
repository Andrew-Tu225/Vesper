import { useState } from 'react'
import { SignalCard } from '@/components/queue/SignalCard'
import { Spinner } from '@/components/ui/Spinner'
import { UpgradeNotice } from '@/components/billing/UpgradeNotice'
import { useSignals, useApprove, useReject, useRewrite } from '@/hooks/useSignals'
import '@/components/queue/queue.css'
import '@/components/ui/ui.css'

type FilterTab = 'all' | 'in_review' | 'scheduled' | 'approved' | 'posted'

const FILTER_TABS: { id: FilterTab; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'in_review', label: 'In Review' },
  { id: 'scheduled', label: 'Scheduled' },
  { id: 'approved', label: 'Approved' },
  { id: 'posted', label: 'Posted' },
]

const EMPTY_MESSAGES: Record<FilterTab, { title: string; sub: string }> = {
  all: { title: 'No signals yet', sub: 'Connect Slack to start capturing content.' },
  in_review: { title: 'Nothing in review', sub: 'All caught up — new signals will appear here.' },
  scheduled: { title: 'Nothing scheduled', sub: 'Approve a draft and pick a publish time.' },
  approved: { title: 'No approved posts', sub: 'Approved posts waiting to publish will appear here.' },
  posted: { title: 'No posts yet', sub: 'Published posts will appear here.' },
}

export default function Queue() {
  const [activeFilter, setActiveFilter] = useState<FilterTab>('all')

  const statusParam = activeFilter === 'all' ? undefined : activeFilter
  const { data, isLoading, isError } = useSignals(statusParam)

  const approve = useApprove()
  const reject = useReject()
  const rewrite = useRewrite()

  const signals = data?.signals ?? []
  const empty = EMPTY_MESSAGES[activeFilter]
  const anyPending = approve.isPending || reject.isPending || rewrite.isPending

  return (
    <div>
      {/* Filter tabs */}
      <div className="queue-filters">
        {FILTER_TABS.map(tab => (
          <button
            key={tab.id}
            className={`queue-filter-tab${activeFilter === tab.id ? ' queue-filter-tab--active' : ''}`}
            onClick={() => setActiveFilter(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <UpgradeNotice />

      {/* States */}
      {isLoading && (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--space-16)' }}>
          <Spinner size="lg" />
        </div>
      )}

      {isError && (
        <div className="error-banner">Failed to load signals. Check your connection and try again.</div>
      )}

      {!isLoading && !isError && signals.length === 0 && (
        <div className="queue-empty">
          <div className="queue-empty__icon">◈</div>
          <div className="queue-empty__title">{empty.title}</div>
          <div className="queue-empty__sub">{empty.sub}</div>
        </div>
      )}

      {!isLoading && !isError && signals.length > 0 && (
        <div className="signal-list">
          {signals.map(signal => (
            <SignalCard
              key={signal.id}
              signal={signal}
              actionPending={anyPending}
              onApprove={(id, variantNumber, body, scheduledAt) =>
                approve.mutate({ id, variant_number: variantNumber, scheduled_at: scheduledAt, ...(body !== undefined && { body_override: body }) })
              }
              onReject={id => reject.mutate({ id })}
              onRewrite={(id, variantNumber, feedback) =>
                rewrite.mutate({ id, variant_number: variantNumber, feedback })
              }
            />
          ))}
        </div>
      )}
    </div>
  )
}
