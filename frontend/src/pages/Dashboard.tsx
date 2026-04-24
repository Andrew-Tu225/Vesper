import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ROUTES } from '@/lib/constants'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import { useSlackStatus } from '@/hooks/useSlackStatus'
import { useLinkedInStatus } from '@/hooks/useLinkedInStatus'
import { useSignals } from '@/hooks/useSignals'
import { useSignalStats } from '@/hooks/useSignalStats'
import type { SignalListItem, ClassificationBucket } from '@/types/api'
import '@/components/ui/ui.css'
import './dashboard.css'

const BANNER_KEY_INCOMPLETE = 'vesper_setup_incomplete_banner_dismissed'
const BANNER_KEY_COMPLETE = 'vesper_setup_complete_banner_dismissed'

const TODAY = new Date().toLocaleDateString('en-US', {
  weekday: 'long',
  month: 'long',
  day: 'numeric',
  year: 'numeric',
})

function XIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
      <path d="M2 6.5L5 9.5L11 3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function ArrowRight() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <path d="M2 6h8M7 3l3 3-3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function SlackIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 54 54" aria-hidden="true">
      <rect width="54" height="54" rx="10" fill="#fff"/>
      <path d="M19.712.133a5.381 5.381 0 0 0-5.376 5.387 5.381 5.381 0 0 0 5.376 5.386h5.376V5.52A5.381 5.381 0 0 0 19.712.133m0 14.365H5.376A5.381 5.381 0 0 0 0 19.884a5.381 5.381 0 0 0 5.376 5.387h14.336a5.381 5.381 0 0 0 5.376-5.387 5.381 5.381 0 0 0-5.376-5.386" fill="#36C5F0"/>
      <path d="M53.76 19.884a5.381 5.381 0 0 0-5.376-5.386 5.381 5.381 0 0 0-5.376 5.386v5.387h5.376a5.381 5.381 0 0 0 5.376-5.387m-14.336 0V5.52A5.381 5.381 0 0 0 34.048.133a5.381 5.381 0 0 0-5.376 5.387v14.364a5.381 5.381 0 0 0 5.376 5.387 5.381 5.381 0 0 0 5.376-5.387" fill="#2EB67D"/>
      <path d="M34.048 54a5.381 5.381 0 0 0 5.376-5.387 5.381 5.381 0 0 0-5.376-5.386h-5.376v5.386A5.381 5.381 0 0 0 34.048 54m0-14.365h14.336a5.381 5.381 0 0 0 5.376-5.386 5.381 5.381 0 0 0-5.376-5.387H34.048a5.381 5.381 0 0 0-5.376 5.387 5.381 5.381 0 0 0 5.376 5.386" fill="#ECB22E"/>
      <path d="M0 34.249a5.381 5.381 0 0 0 5.376 5.386 5.381 5.381 0 0 0 5.376-5.386v-5.387H5.376A5.381 5.381 0 0 0 0 34.249m14.336 0v14.364A5.381 5.381 0 0 0 19.712 54a5.381 5.381 0 0 0 5.376-5.387V34.249a5.381 5.381 0 0 0-5.376-5.387 5.381 5.381 0 0 0-5.376 5.387" fill="#E01E5A"/>
    </svg>
  )
}

function LinkedInIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" aria-hidden="true">
      <rect width="24" height="24" rx="5" fill="#0A66C2"/>
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452z" fill="white"/>
    </svg>
  )
}

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return days === 1 ? 'yesterday' : `${days}d ago`
}

function SignalCard({ signal }: { signal: SignalListItem }) {
  return (
    <div className="signal-card" data-testid="signal-card">
      <div className="signal-card__header">
        <span className="signal-source" data-source={signal.source_type}>
          {signal.source_type === 'slack' ? '#' : '✉'}
        </span>
        <span className="signal-card__channel">{signal.source_channel ?? '—'}</span>
        {signal.signal_type && (
          <span className="signal-badge" data-type={signal.signal_type}>
            {signal.signal_type.replace(/_/g, ' ')}
          </span>
        )}
        <span className="signal-card__time">{formatRelative(signal.created_at)}</span>
      </div>
      <p className="signal-card__summary">{signal.summary ?? ''}</p>
    </div>
  )
}

function SignalCardSkeleton() {
  return <div className="signal-card signal-card--skeleton" aria-hidden="true" />
}

interface IntegrationsPanelProps {
  slack: { connected: boolean; workspace_name?: string | undefined; channel_count?: number | undefined } | undefined
  linkedin: { connected: boolean } | undefined
}

function IntegrationsPanel({ slack, linkedin }: IntegrationsPanelProps) {
  return (
    <div className="side-panel">
      <p className="side-panel__header">Integrations</p>
      <div className="side-panel__body">
        <div className="side-int-row">
          <span className={`side-int-icon${slack?.connected ? '' : ' side-int-icon--off'}`}>
            <SlackIcon />
          </span>
          <div className="side-int-row__body">
            <p className="side-int-row__title">Slack</p>
            <p className="side-int-row__sub">
              {slack?.connected
                ? `${slack.channel_count ?? 0} channel${(slack.channel_count ?? 0) !== 1 ? 's' : ''} monitored`
                : 'Not connected'}
            </p>
          </div>
        </div>
        <div className="side-int-row">
          <span className={`side-int-icon${linkedin?.connected ? '' : ' side-int-icon--off'}`}>
            <LinkedInIcon />
          </span>
          <div className="side-int-row__body">
            <p className="side-int-row__title">LinkedIn</p>
            <p className="side-int-row__sub">
              {linkedin?.connected ? 'Company page connected' : 'Not connected'}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

interface ClassificationMixProps {
  buckets: ClassificationBucket[] | undefined
}

function ClassificationMix({ buckets }: ClassificationMixProps) {
  return (
    <div className="side-panel">
      <p className="side-panel__header">Classification mix</p>
      <div className="side-panel__body">
        {buckets === undefined ? (
          [1, 2, 3, 4, 5].map(i => (
            <div className="mix-row mix-row--skeleton" key={i} aria-hidden="true">
              <div className="mix-bar"><div className="mix-bar__fill" style={{ width: '0%' }} /></div>
            </div>
          ))
        ) : buckets.length === 0 || buckets.every(b => b.count === 0) ? (
          <p className="signals-feed__empty signals-feed__empty--sm">No data yet</p>
        ) : (
          buckets.map(({ signal_type, percent }) => (
            <div className="mix-row" key={signal_type}>
              <div className="mix-row__meta">
                <span className="mix-row__label">{signal_type.replace(/_/g, ' ')}</span>
                <span className="mix-row__percent">{percent}%</span>
              </div>
              <div className="mix-bar">
                <div className="mix-bar__fill" data-type={signal_type} style={{ width: `${percent}%` }} />
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { data: user } = useCurrentUser()
  const [params] = useSearchParams()
  const error = params.get('error')

  const { data: slack } = useSlackStatus()
  const { data: linkedin } = useLinkedInStatus()
  const { data: signalsData, isLoading: signalsLoading } = useSignals()
  const { data: stats } = useSignalStats()

  const slackConnected = slack?.connected ?? false
  const slackChannelsOk = slack?.channels_configured ?? false
  const linkedinConnected = linkedin?.connected ?? false

  const setupComplete = slackConnected && linkedinConnected && slackChannelsOk

  const [incompleteDismissed, setIncompleteDismissed] = useState(
    () => localStorage.getItem(BANNER_KEY_INCOMPLETE) === 'true'
  )
  const [completeDismissed, setCompleteDismissed] = useState(
    () => localStorage.getItem(BANNER_KEY_COMPLETE) === 'true'
  )

  function dismissIncomplete() {
    localStorage.setItem(BANNER_KEY_INCOMPLETE, 'true')
    setIncompleteDismissed(true)
  }

  function dismissComplete() {
    localStorage.setItem(BANNER_KEY_COMPLETE, 'true')
    setCompleteDismissed(true)
  }

  const firstName = user?.display_name?.split(' ')[0] ?? 'there'
  const signals = signalsData?.signals ?? []

  return (
    <div className="dashboard">
      {error && (
        <div className="error-banner">
          Authentication error: {error}
        </div>
      )}

      {!setupComplete && !incompleteDismissed && (
        <div className="setup-banner setup-banner--incomplete" role="alert">
          <span className="setup-banner__text">
            Your pipeline setup isn't complete yet. Finish all three steps to start capturing signals.
          </span>
          <button className="setup-banner__close" onClick={dismissIncomplete} aria-label="Dismiss">
            <XIcon />
          </button>
        </div>
      )}

      {setupComplete && !completeDismissed && (
        <div className="setup-banner setup-banner--complete" role="status">
          <span className="setup-banner__text">
            Setup complete — your pipeline is live and ready to capture content signals.
          </span>
          <button className="setup-banner__close" onClick={dismissComplete} aria-label="Dismiss">
            <XIcon />
          </button>
        </div>
      )}

      <header>
        <p className="dashboard__eyebrow">{TODAY}</p>
        <h1 className="dashboard__title">Welcome back, {firstName}</h1>
        <p className="dashboard__sub">
          {setupComplete
            ? "Here's what's been captured in the last 7 days."
            : 'Your content pipeline is ready. Connect your workspace to start capturing signals.'}
        </p>
      </header>

      <section className="dashboard__stats" aria-label="Activity overview">
        <div className="stat-card">
          <span className="stat-card__label">Signals detected</span>
          <span className="stat-card__value">{stats?.total_signals_this_week ?? '—'}</span>
          <span className="stat-card__sub">this week</span>
        </div>
        <div className="stat-card">
          <span className="stat-card__label">Drafts ready</span>
          <span className="stat-card__value stat-card__value--accent">{stats?.drafts_awaiting_review ?? '—'}</span>
          <span className="stat-card__sub">awaiting your review</span>
        </div>
        <div className="stat-card">
          <span className="stat-card__label">Posts published</span>
          <span className="stat-card__value">{stats?.posts_published_this_month ?? '—'}</span>
          <span className="stat-card__sub">this month</span>
        </div>
      </section>

      {setupComplete && (
        <section>
          <div className="signals-section">
            <div className="signals-section__head">
              <p className="dashboard__section-label">Recent signals</p>
            </div>
          <div className="dashboard__live">
            <div className="signals-feed">
              {signalsLoading && !signalsData ? (
                [1, 2, 3].map(i => <SignalCardSkeleton key={i} />)
              ) : signals.length === 0 ? (
                <p className="signals-feed__empty" data-testid="signals-empty">
                  No signals captured yet. They'll appear here as Vesper monitors your channels.
                </p>
              ) : (
                signals.map(signal => (
                  <SignalCard key={signal.id} signal={signal} />
                ))
              )}
            </div>
            <div className="dashboard__sidebar">
              <IntegrationsPanel slack={slack} linkedin={linkedin} />
              <ClassificationMix buckets={stats?.classification_mix} />
            </div>
          </div>
          </div>
        </section>
      )}

      {!setupComplete && (
        <section>
          <p className="dashboard__section-label">Getting started</p>
          <div className="onboarding-card">
            <div className="onboarding-card__header">
              <h2 className="onboarding-card__title">Set up your pipeline</h2>
              <p className="onboarding-card__desc">
                Three steps to your first AI-drafted LinkedIn post — none of them take more than two minutes.
              </p>
            </div>

            <div className="onboarding-step">
              <div className={`onboarding-step__indicator${slackConnected ? ' onboarding-step__indicator--done' : ' onboarding-step__indicator--active'}`}>
                {slackConnected ? <CheckIcon /> : '1'}
              </div>
              <div className="onboarding-step__body">
                <p className="onboarding-step__title">Connect your Slack workspace</p>
                <p className="onboarding-step__sub">
                  {slackConnected
                    ? `Connected to ${slack?.workspace_name}${slackChannelsOk ? ` · ${slack?.channel_count} channel${(slack?.channel_count ?? 0) !== 1 ? 's' : ''} monitored` : ' · no channels configured yet'}`
                    : 'Choose which channels Vesper should monitor for content signals.'}
                </p>
              </div>
              {slackConnected ? (
                <a href="/settings" className="onboarding-step__cta onboarding-step__cta--secondary">
                  Manage <ArrowRight />
                </a>
              ) : (
                <a href="/api/oauth/slack/install" className="onboarding-step__cta">
                  Connect <ArrowRight />
                </a>
              )}
            </div>

            <div className="onboarding-step">
              <div className={`onboarding-step__indicator${linkedinConnected ? ' onboarding-step__indicator--done' : ''}`}>
                {linkedinConnected ? <CheckIcon /> : '2'}
              </div>
              <div className="onboarding-step__body">
                <p className="onboarding-step__title">Connect LinkedIn</p>
                <p className="onboarding-step__sub">
                  {linkedinConnected
                    ? 'LinkedIn connected — drafts can be published automatically.'
                    : 'Authorize posting to your company page so approved drafts can publish automatically.'}
                </p>
              </div>
              {linkedinConnected ? (
                <a href="/settings" className="onboarding-step__cta onboarding-step__cta--secondary">
                  Manage <ArrowRight />
                </a>
              ) : slackConnected ? (
                <a href="/api/oauth/linkedin/install" className="onboarding-step__cta">
                  Connect <ArrowRight />
                </a>
              ) : (
                <span className="onboarding-step__cta onboarding-step__cta--disabled" aria-disabled="true">
                  Connect <ArrowRight />
                </span>
              )}
            </div>

            <div className="onboarding-step">
              <div className={`onboarding-step__indicator${slackChannelsOk ? ' onboarding-step__indicator--done' : slackConnected ? ' onboarding-step__indicator--active' : ''}`}>
                {slackChannelsOk ? <CheckIcon /> : '3'}
              </div>
              <div className="onboarding-step__body">
                <p className="onboarding-step__title">Slack Channels Setup</p>
                <p className="onboarding-step__sub">
                  {slackChannelsOk
                    ? `${slack?.channel_count} channel${(slack?.channel_count ?? 0) !== 1 ? 's' : ''} monitored`
                    : 'Pick which Slack channels Vesper should monitor for content signals.'}
                </p>
              </div>
              {slackChannelsOk ? (
                <a href="/settings" className="onboarding-step__cta onboarding-step__cta--secondary">
                  Manage <ArrowRight />
                </a>
              ) : slackConnected ? (
                <Link to={ROUTES.CHANNEL_SETUP} className="onboarding-step__cta">
                  Set up <ArrowRight />
                </Link>
              ) : (
                <span className="onboarding-step__cta onboarding-step__cta--disabled" aria-disabled="true">
                  Set up <ArrowRight />
                </span>
              )}
            </div>
          </div>
        </section>
      )}
    </div>
  )
}