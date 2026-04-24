import type { CalendarEvent, WeekRange } from '@/types/calendar'

export const HOUR_START = 8
export const HOUR_END = 18
export const ROW_HEIGHT_PX = 64

export function computeHourRange(events: CalendarEvent[]): { hourStart: number; hourEnd: number } {
  if (events.length === 0) return { hourStart: HOUR_START, hourEnd: HOUR_END }
  let minHour = HOUR_START
  let maxHour = HOUR_END
  for (const e of events) {
    const h = e.occursAt.getHours()
    if (h < minHour) minHour = h
    if (h > maxHour) maxHour = h
  }
  return {
    hourStart: Math.max(0, minHour - 1),
    hourEnd: Math.min(23, maxHour + 2),
  }
}

const MONTH_NAMES = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
]

function getMondayOf(date: Date): Date {
  const d = new Date(date)
  const day = d.getDay()
  const diff = day === 0 ? -6 : 1 - day
  d.setDate(d.getDate() + diff)
  d.setHours(0, 0, 0, 0)
  return d
}

function formatWeekLabel(start: Date, end: Date): string {
  const sMonth = MONTH_NAMES[start.getMonth()]
  const eMonth = MONTH_NAMES[end.getMonth()]
  const year = end.getFullYear()
  if (start.getMonth() === end.getMonth()) {
    return `${sMonth} ${start.getDate()} – ${end.getDate()}, ${year}`
  }
  return `${sMonth} ${start.getDate()} – ${eMonth} ${end.getDate()}, ${year}`
}

export function getWeekRange(anchor: Date): WeekRange {
  const start = getMondayOf(anchor)
  const days: Date[] = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(start)
    d.setDate(start.getDate() + i)
    return d
  })
  const end = days[6] as Date
  return { start, end, days, label: formatWeekLabel(start, end) }
}

export function shiftWeek(range: WeekRange, direction: -1 | 1): WeekRange {
  const anchor = new Date(range.start)
  anchor.setDate(anchor.getDate() + direction * 7)
  return getWeekRange(anchor)
}

export function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  )
}

export function bucketEventsByDay(events: CalendarEvent[], days: Date[]): CalendarEvent[][] {
  return days.map(day => events.filter(e => isSameDay(e.occursAt, day)))
}

export function slotTopPx(date: Date, hourStart = HOUR_START): number {
  const hours = date.getHours() + date.getMinutes() / 60
  return Math.max(0, (hours - hourStart) * ROW_HEIGHT_PX)
}

export function formatEventTime(date: Date): string {
  return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
}
