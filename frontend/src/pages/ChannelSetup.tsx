import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ROUTES } from '@/lib/constants'
import '@/components/ui/ui.css'
import './channel-setup.css'

interface Channel {
  id: string
  name: string
  member_count: number
}

async function fetchChannels(): Promise<Channel[]> {
  const res = await fetch('/api/onboarding/channels')
  if (!res.ok) throw new Error('Failed to load channels')
  const data = await res.json()
  return data.channels
}

async function saveChannels(channelIds: string[]): Promise<void> {
  const res = await fetch('/api/onboarding/channels', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ channel_ids: channelIds }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? 'Failed to save channels')
  }
}

export default function ChannelSetup() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [saveError, setSaveError] = useState<string | null>(null)

  const { data: channels, isLoading, error } = useQuery({
    queryKey: ['channels'],
    queryFn: fetchChannels,
  })

  const mutation = useMutation({
    mutationFn: saveChannels,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['slackStatus'] })
      navigate(ROUTES.DASHBOARD)
    },
    onError: (err: Error) => setSaveError(err.message),
  })

  function toggleChannel(id: string) {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaveError(null)
    mutation.mutate(Array.from(selected))
  }

  return (
    <div className="channel-setup">
      <header className="channel-setup__header">
        <p className="channel-setup__eyebrow">Slack</p>
        <h1 className="channel-setup__title">Slack Channels Setup</h1>
        <p className="channel-setup__sub">
          Vesper will watch these channels for content signals worth turning into LinkedIn posts.
          You can change this any time from Settings.
        </p>
      </header>

      <div className="channel-setup__notice">
        <span className="channel-setup__notice-icon">💬</span>
        <p className="channel-setup__notice-body">
          <strong>Before continuing:</strong> create a channel called{' '}
          <code>#vesper-ai</code> in your Slack workspace, then run{' '}
          <code>/invite @Vesper</code> inside it. Vesper will send LinkedIn
          drafts there for your team to review and approve.
        </p>
      </div>

      <div className="channel-setup__notice">
        <span className="channel-setup__notice-icon">⚠️</span>
        <p className="channel-setup__notice-body">
          <strong>Important:</strong> Vesper needs to be a member of every
          channel you select below. In each channel you want to monitor, run{' '}
          <code>/invite @Vesper</code> before saving. Channels the bot hasn't
          joined will be silently skipped during scanning.
        </p>
      </div>

      <div className="channel-setup__card">
        {isLoading && (
          <div className="channel-setup__state">Loading channels…</div>
        )}

        {error && (
          <div className="channel-setup__state channel-setup__state--error">
            Could not load channels. Make sure your Slack workspace is connected.
          </div>
        )}

        {channels && channels.length === 0 && (
          <div className="channel-setup__state">
            No channels found. The Vesper bot may need to be invited to channels first.
          </div>
        )}

        {channels && channels.length > 0 && (
          <form onSubmit={handleSubmit}>
            <ul className="channel-list">
              {channels.map(ch => (
                <li key={ch.id} className="channel-item">
                  <label className="channel-item__label">
                    <input
                      type="checkbox"
                      className="channel-item__checkbox"
                      checked={selected.has(ch.id)}
                      onChange={() => toggleChannel(ch.id)}
                    />
                    <span className="channel-item__name">#{ch.name}</span>
                    <span className="channel-item__count">{ch.member_count} members</span>
                  </label>
                </li>
              ))}
            </ul>

            {saveError && (
              <p className="channel-setup__error">{saveError}</p>
            )}

            <div className="channel-setup__actions">
              <button
                type="button"
                className="channel-setup__cancel"
                onClick={() => navigate(ROUTES.DASHBOARD)}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="channel-setup__submit"
                disabled={selected.size === 0 || mutation.isPending}
              >
                {mutation.isPending ? 'Saving…' : `Save ${selected.size > 0 ? `${selected.size} ` : ''}channel${selected.size !== 1 ? 's' : ''}`}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}