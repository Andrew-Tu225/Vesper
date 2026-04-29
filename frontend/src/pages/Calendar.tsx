import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { EventCard } from '@/components/calendar/EventCard'
import { EventModal } from '@/components/calendar/EventModal'
import { UpgradeNotice } from '@/components/billing/UpgradeNotice'
import {
  getWeekRange,
  shiftWeek,
  isSameDay,
  bucketEventsByDay,
  slotTopPx,
  computeHourRange,
  ROW_HEIGHT_PX,
} from '@/lib/calendar'
import { useCalendarEvents } from '@/hooks/useCalendarEvents'
import '@/components/calendar/calendar.css'
import '@/components/queue/queue.css'
import type { CalendarEvent } from '@/types/calendar'

const DAY_NAMES = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']

function ChevronLeft() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M9 11L5 7l4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function ChevronRight() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M5 11l4-4-4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function PlusIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M7 2v10M2 7h10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function formatHour(h: number): string {
  if (h === 12) return '12 PM'
  return h < 12 ? `${h} AM` : `${h - 12} PM`
}

export default function Calendar() {
  const navigate = useNavigate()
  const [range, setRange] = useState(() => getWeekRange(new Date()))
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null)

  const { events, isLoading, isError } = useCalendarEvents()

  const today = new Date()
  const eventsByDay = bucketEventsByDay(events, range.days)

  const { hourStart, hourEnd } = computeHourRange(events)
  const HOURS = Array.from({ length: hourEnd - hourStart }, (_, i) => hourStart + i)
  const GRID_HEIGHT = (hourEnd - hourStart) * ROW_HEIGHT_PX

  function handlePrev() { setRange(r => shiftWeek(r, -1)) }
  function handleNext() { setRange(r => shiftWeek(r, 1)) }
  function handleToday() { setRange(getWeekRange(new Date())) }

  return (
    <div>
      <header className="calendar-page__header">
        <div>
          <h1 className="calendar-page__title">Calendar</h1>
          <p className="calendar-page__sub">Schedule approved posts and monitor publishing windows.</p>
        </div>
        <button
          className="calendar-page__schedule-btn"
          onClick={() => navigate('/queue?filter=approved')}
        >
          <PlusIcon />
          Schedule post
        </button>
      </header>

      <UpgradeNotice />

      <div className="calendar-surface">

        <div className="cal-nav">
          <div className="cal-nav__arrows">
            <button className="cal-nav__arrow" onClick={handlePrev} aria-label="Previous week">
              <ChevronLeft />
            </button>
            <button className="cal-nav__arrow" onClick={handleNext} aria-label="Next week">
              <ChevronRight />
            </button>
          </div>
          <span className="cal-nav__range">{range.label}</span>
          <button className="cal-nav__today-btn" onClick={handleToday}>Today</button>
          <div className="cal-nav__legend">
            <span className="cal-legend-chip cal-legend-chip--posted">
              <span className="cal-legend-chip__dot" /> Published
            </span>
            <span className="cal-legend-chip cal-legend-chip--scheduled">
              <span className="cal-legend-chip__dot" /> Scheduled
            </span>
          </div>
        </div>

        {isError && (
          <p className="cal-empty">Failed to load events. Please try again.</p>
        )}

        {!isError && (
          <div className="cal-grid-wrapper">

            <div className="cal-day-header-row">
              <div className="cal-day-header-row__gutter" />
              {range.days.map((day, i) => (
                <div
                  key={i}
                  className={`cal-day-header${isSameDay(day, today) ? ' cal-day-header--today' : ''}`}
                >
                  <span className="cal-day-header__name">{DAY_NAMES[i]}</span>
                  <span className="cal-day-header__date">{day.getDate()}</span>
                </div>
              ))}
            </div>

            {isLoading ? (
              <div className="cal-empty">Loading events…</div>
            ) : (
              <div className="cal-body" style={{ height: GRID_HEIGHT }}>

                <div className="cal-time-axis">
                  {HOURS.map(h => (
                    <span
                      key={h}
                      className="cal-time-label"
                      style={{ top: (h - hourStart) * ROW_HEIGHT_PX }}
                    >
                      {formatHour(h)}
                    </span>
                  ))}
                </div>

                {range.days.map((_day, colIdx) => (
                  <div key={colIdx} className="cal-day-col">
                    {HOURS.map(h => (
                      <div
                        key={h}
                        className="cal-hour-line"
                        style={{ top: (h - hourStart) * ROW_HEIGHT_PX }}
                      />
                    ))}

                    {(eventsByDay[colIdx] ?? []).map(event => (
                      <div
                        key={event.id}
                        style={{
                          position: 'absolute',
                          top: slotTopPx(event.occursAt, hourStart),
                          left: 0,
                          right: 0,
                        }}
                      >
                        <EventCard event={event} onClick={setSelectedEvent} />
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {selectedEvent && (
        <EventModal event={selectedEvent} onClose={() => setSelectedEvent(null)} />
      )}
    </div>
  )
}