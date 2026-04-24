export type CalendarEventStatus = 'scheduled' | 'posted'

export interface CalendarEvent {
  id: string
  signalId: string
  title: string
  status: CalendarEventStatus
  occursAt: Date
  metaLine: string
  draftBody: string
  signalSummary: string | null
}

export interface WeekRange {
  start: Date
  end: Date
  days: Date[]
  label: string
}