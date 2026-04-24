import { useEffect } from 'react'
import { StatusBadge } from '@/components/queue/StatusBadge'
import { formatEventTime } from '@/lib/calendar'
import type { CalendarEvent } from '@/types/calendar'

interface EventModalProps {
  event: CalendarEvent
  onClose: () => void
}

export function EventModal({ event, onClose }: EventModalProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  const timeLabel = formatEventTime(event.occursAt)
  const dateLabel = event.occursAt.toLocaleDateString('en-US', {
    weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
  })

  return (
    <div className="cal-modal-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-label={event.title}>
      <div className="cal-modal" onClick={e => e.stopPropagation()}>
        <div className="cal-modal__header">
          <div className="cal-modal__title-row">
            <h2 className="cal-modal__title">{event.title}</h2>
            <StatusBadge status={event.status} />
          </div>
          <p className="cal-modal__time">{timeLabel} · {dateLabel}</p>
        </div>

        {event.signalSummary && (
          <div className="cal-modal__section">
            <p className="cal-modal__section-label">Signal</p>
            <p className="cal-modal__signal-summary">{event.signalSummary}</p>
          </div>
        )}

        <div className="cal-modal__section">
          <p className="cal-modal__section-label">Draft</p>
          <div className="cal-modal__draft-body">{event.draftBody}</div>
        </div>

        <div className="cal-modal__footer">
          <button className="cal-modal__close-btn" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  )
}