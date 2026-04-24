import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'
import { StatusBadge } from './StatusBadge'
import { useSignal } from '@/hooks/useSignals'
import type { SignalListItem } from '@/types/api'
import './queue.css'

const SIGNAL_TYPE_LABELS: Record<string, string> = {
  customer_praise: 'Customer Praise',
  product_win: 'Product Win',
  launch_update: 'Launch Update',
  hiring: 'Hiring',
  founder_insight: 'Founder Insight',
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

interface Props {
  signal: SignalListItem
  onApprove: (signalId: string, variantNumber: number, body: string | undefined, scheduledAt: string) => void
  onReject: (signalId: string) => void
  onRewrite: (signalId: string, variantNumber: number, feedback: string) => void
  actionPending?: boolean
}

export function SignalCard({ signal, onApprove, onReject, onRewrite, actionPending }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [activeVariant, setActiveVariant] = useState(0)
  const [panel, setPanel] = useState<'approve' | 'rewrite' | null>(null)
  const [approveBody, setApproveBody] = useState('')
  const [scheduledAt, setScheduledAt] = useState('')
  const [feedback, setFeedback] = useState('')

  // Only fetch detail when expanded
  const { data: detail, isLoading: detailLoading } = useSignal(signal.id, expanded)

  const drafts = detail?.draft_posts ?? []
  const currentDraft = drafts[activeVariant] ?? null
  const isActionable = signal.status === 'in_review'

  function handleExpand() {
    if (expanded) setActiveVariant(0)
    setExpanded(v => !v)
    setPanel(null)
  }

  function handleVariantChange(idx: number) {
    setActiveVariant(idx)
    setApproveBody(drafts[idx]?.body ?? '')
    setPanel(null)
  }

  function handleOpenApprove() {
    setApproveBody(currentDraft?.body ?? '')
    setPanel(p => (p === 'approve' ? null : 'approve'))
  }

  function handleOpenRewrite() {
    setFeedback('')
    setPanel(p => (p === 'rewrite' ? null : 'rewrite'))
  }

  function handleApproveSubmit() {
    if (!scheduledAt || !currentDraft) return
    const bodyChanged = approveBody !== currentDraft.body
    onApprove(signal.id, currentDraft.variant_number, bodyChanged ? approveBody : undefined, new Date(scheduledAt).toISOString())
    setScheduledAt('')
    setPanel(null)
  }

  function handleRewriteSubmit() {
    if (!feedback.trim() || !currentDraft) return
    onRewrite(signal.id, currentDraft.variant_number, feedback)
    setFeedback('')
    setPanel(null)
  }

  return (
    <div className={`signal-card${expanded ? ' signal-card--expanded' : ''}`}>
      {/* Header — always visible */}
      <div
        className="signal-card__header"
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        onClick={handleExpand}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') handleExpand() }}
      >
        <span className="signal-card__type">
          {SIGNAL_TYPE_LABELS[signal.signal_type ?? ''] ?? signal.signal_type ?? 'Signal'}
        </span>
        <span className="signal-card__summary">
          {signal.summary ?? 'No summary'}
        </span>
        <div className="signal-card__meta">
          <StatusBadge status={signal.status} />
          <span className="signal-card__time">{relativeTime(signal.created_at)}</span>
          <svg
            className={`signal-card__chevron${expanded ? ' signal-card__chevron--open' : ''}`}
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <path d="M4 6l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>

      {/* Expanded body */}
      {expanded && (
        <div className="signal-card__body">
          {detailLoading && (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--space-6)' }}>
              <Spinner />
            </div>
          )}

          {!detailLoading && (
            <>
              {signal.summary && (
                <p className="signal-card__summary-full">{signal.summary}</p>
              )}

              {drafts.length > 1 && (
                <div className="variant-tabs">
                  {drafts.map((d, idx) => (
                    <button
                      key={d.id}
                      className={`variant-tab${activeVariant === idx ? ' variant-tab--active' : ''}`}
                      onClick={() => handleVariantChange(idx)}
                    >
                      Variant {idx + 1}
                    </button>
                  ))}
                </div>
              )}

              {currentDraft ? (
                <div className="draft-body">{currentDraft.body}</div>
              ) : (
                <div className="draft-body" style={{ color: 'var(--color-text-disabled)', fontStyle: 'italic' }}>
                  No draft available yet.
                </div>
              )}

              {panel === 'approve' && (
                <div className="approve-panel">
                  <span className="approve-panel__label">Edit post before scheduling</span>
                  <textarea
                    className="approve-panel__textarea"
                    value={approveBody}
                    onChange={e => setApproveBody(e.target.value)}
                    maxLength={3000}
                  />
                  <div className="approve-panel__row">
                    <span className="approve-panel__label">Schedule for</span>
                    <input
                      type="datetime-local"
                      className="approve-panel__datetime"
                      value={scheduledAt}
                      min={new Date().toISOString().slice(0, 16)}
                      onChange={e => setScheduledAt(e.target.value)}
                    />
                    <div style={{ flex: 1 }} />
                    <Button variant="ghost" onClick={() => setPanel(null)}>Cancel</Button>
                    <Button
                      variant="primary"
                      disabled={!scheduledAt || new Date(scheduledAt) <= new Date() || actionPending}
                      onClick={handleApproveSubmit}
                    >
                      Confirm
                    </Button>
                  </div>
                </div>
              )}

              {panel === 'rewrite' && (
                <div className="rewrite-panel">
                  <textarea
                    className="rewrite-panel__textarea"
                    placeholder="What should be different? (e.g. make it shorter, more casual, lead with the outcome)"
                    value={feedback}
                    onChange={e => setFeedback(e.target.value)}
                    maxLength={500}
                  />
                  <div className="rewrite-panel__row">
                    <Button variant="ghost" onClick={() => setPanel(null)}>Cancel</Button>
                    <Button
                      variant="secondary"
                      disabled={!feedback.trim() || actionPending}
                      onClick={handleRewriteSubmit}
                    >
                      Request rewrite
                    </Button>
                    <span className="rewrite-panel__char-count">{feedback.length}/500</span>
                  </div>
                </div>
              )}

              {signal.status === 'scheduled' && currentDraft?.scheduled_at && (
                <div className="scheduled-info">
                  <svg className="scheduled-info__icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <rect x="2" y="3" width="12" height="12" rx="2" />
                    <path d="M5 1v4M11 1v4M2 7h12" strokeLinecap="round" />
                  </svg>
                  Scheduled for {new Date(currentDraft.scheduled_at).toLocaleString()}
                </div>
              )}

              {isActionable && (
                <div className="signal-card__actions">
                  <Button variant="primary" onClick={handleOpenApprove} disabled={!currentDraft || actionPending}>
                    {panel === 'approve' ? 'Cancel approve' : 'Approve'}
                  </Button>
                  <Button variant="secondary" onClick={handleOpenRewrite} disabled={!currentDraft || actionPending}>
                    {panel === 'rewrite' ? 'Cancel rewrite' : 'Rewrite'}
                  </Button>
                  <Button variant="ghost" onClick={() => onReject(signal.id)} disabled={actionPending}>
                    Reject
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
