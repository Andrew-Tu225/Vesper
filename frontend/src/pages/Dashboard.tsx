import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ROUTES } from '@/lib/constants'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import { useSlackStatus } from '@/hooks/useSlackStatus'
import { useLinkedInStatus } from '@/hooks/useLinkedInStatus'
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

export default function Dashboard() {
  const { data: user } = useCurrentUser()
  const [params] = useSearchParams()
  const error = params.get('error')

  const { data: slack } = useSlackStatus()
  const { data: linkedin } = useLinkedInStatus()

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

      {/* Welcome header */}
      <header>
        <p className="dashboard__eyebrow">{TODAY}</p>
        <h1 className="dashboard__title">Welcome back, {firstName}</h1>
        <p className="dashboard__sub">
          Your content pipeline is ready. Connect your workspace to start capturing signals.
        </p>
      </header>

      {/* Stat strip */}
      <section className="dashboard__stats" aria-label="Activity overview">
        <div className="stat-card">
          <span className="stat-card__label">Signals detected</span>
          <span className="stat-card__value">0</span>
          <span className="stat-card__sub">this week</span>
        </div>
        <div className="stat-card">
          <span className="stat-card__label">Drafts ready</span>
          <span className="stat-card__value stat-card__value--accent">0</span>
          <span className="stat-card__sub">awaiting your review</span>
        </div>
        <div className="stat-card">
          <span className="stat-card__label">Posts published</span>
          <span className="stat-card__value">0</span>
          <span className="stat-card__sub">this month</span>
        </div>
      </section>

      {/* Getting started */}
      <section>
        <p className="dashboard__section-label">Getting started</p>
        <div className="onboarding-card">
          <div className="onboarding-card__header">
            <h2 className="onboarding-card__title">Set up your pipeline</h2>
            <p className="onboarding-card__desc">
              Three steps to your first AI-drafted LinkedIn post — none of them take more than two minutes.
            </p>
          </div>

          {/* Step 1 — Slack */}
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

          {/* Step 2 — LinkedIn */}
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

          {/* Step 3 — Channel setup */}
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
    </div>
  )
}