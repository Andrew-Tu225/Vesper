import { useSearchParams } from 'react-router-dom'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import '@/components/ui/ui.css'
import './dashboard.css'

const TODAY = new Date().toLocaleDateString('en-US', {
  weekday: 'long',
  month: 'long',
  day: 'numeric',
  year: 'numeric',
})

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

  const firstName = user?.display_name?.split(' ')[0] ?? 'there'

  return (
    <div className="dashboard">
      {error && (
        <div className="error-banner">
          Authentication error: {error}
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

          <div className="onboarding-step">
            <div className="onboarding-step__indicator onboarding-step__indicator--active">1</div>
            <div className="onboarding-step__body">
              <p className="onboarding-step__title">Connect your Slack workspace</p>
              <p className="onboarding-step__sub">Choose which channels Vesper should monitor for content signals.</p>
            </div>
            <a href="/settings" className="onboarding-step__cta">
              Connect <ArrowRight />
            </a>
          </div>

          <div className="onboarding-step">
            <div className="onboarding-step__indicator">2</div>
            <div className="onboarding-step__body">
              <p className="onboarding-step__title">Connect LinkedIn</p>
              <p className="onboarding-step__sub">Authorize posting to your company page so approved drafts can publish automatically.</p>
            </div>
            <a href="/settings" className="onboarding-step__cta onboarding-step__cta--secondary">
              Connect <ArrowRight />
            </a>
          </div>

          <div className="onboarding-step">
            <div className="onboarding-step__indicator">3</div>
            <div className="onboarding-step__body">
              <p className="onboarding-step__title">Seed your style library</p>
              <p className="onboarding-step__sub">Add 5 of your best past posts so Vesper can match your brand voice.</p>
            </div>
            <a href="/style-library" className="onboarding-step__cta onboarding-step__cta--disabled" aria-disabled="true">
              Add posts <ArrowRight />
            </a>
          </div>
        </div>
      </section>
    </div>
  )
}