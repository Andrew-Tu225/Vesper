import { useQuery, useQueries } from '@tanstack/react-query'
import { fetchSignals, fetchSignal } from '@/lib/signals'
import { formatEventTime } from '@/lib/calendar'
import type { CalendarEvent } from '@/types/calendar'
import type { SignalDetail } from '@/types/api'

function toCalendarEvent(signal: SignalDetail): CalendarEvent | null {
  const draft = signal.draft_posts.find(d => d.is_selected) ?? signal.draft_posts[0]
  if (!draft) return null

  const timeStr = signal.status === 'posted' ? draft.published_at : draft.scheduled_at
  if (!timeStr) return null

  const occursAt = new Date(timeStr)
  const status = signal.status === 'posted' ? ('posted' as const) : ('scheduled' as const)
  const metaLine = status === 'posted'
    ? 'Published'
    : `${formatEventTime(occursAt)} · scheduled`

  return {
    id: `${signal.id}-${draft.id}`,
    signalId: signal.id,
    title: signal.summary ?? 'Untitled post',
    status,
    occursAt,
    metaLine,
    draftBody: draft.body,
    signalSummary: signal.summary,
  }
}

export function useCalendarEvents() {
  const scheduledQ = useQuery({
    queryKey: ['signals', 'scheduled'],
    queryFn: () => fetchSignals('scheduled', 1, 100),
  })
  const postedQ = useQuery({
    queryKey: ['signals', 'posted'],
    queryFn: () => fetchSignals('posted', 1, 100),
  })

  const allIds = [
    ...(scheduledQ.data?.signals ?? []),
    ...(postedQ.data?.signals ?? []),
  ].map(s => s.id)

  const detailQueries = useQueries({
    queries: allIds.map(id => ({
      queryKey: ['signal', id],
      queryFn: () => fetchSignal(id),
    })),
  })

  const isLoading =
    scheduledQ.isLoading ||
    postedQ.isLoading ||
    detailQueries.some(q => q.isLoading)

  const isError =
    scheduledQ.isError ||
    postedQ.isError ||
    detailQueries.some(q => q.isError)

  const events: CalendarEvent[] = detailQueries
    .map(q => q.data)
    .filter((d): d is SignalDetail => d != null)
    .flatMap(signal => {
      const event = toCalendarEvent(signal)
      return event ? [event] : []
    })

  return { events, isLoading, isError }
}