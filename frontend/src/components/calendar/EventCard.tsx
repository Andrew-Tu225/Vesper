import type { CalendarEvent } from '@/types/calendar'

interface EventCardProps {
  event: CalendarEvent
  onClick: (event: CalendarEvent) => void
}

export function EventCard({ event, onClick }: EventCardProps) {
  return (
    <button
      className={`cal-event cal-event--${event.status}`}
      onClick={() => onClick(event)}
      title={event.title}
    >
      <span className="cal-event__title">{event.title}</span>
      <span className="cal-event__meta">{event.metaLine}</span>
    </button>
  )
}