import { useState } from 'react'
import { useSlackStatus } from '@/hooks/useSlackStatus'
import { useLinkedInStatus } from '@/hooks/useLinkedInStatus'
import './settings.css'

function SlackLogo() {
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

function LinkedInLogo() {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" aria-hidden="true">
      <rect width="24" height="24" rx="5" fill="#0A66C2"/>
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452z" fill="white"/>
    </svg>
  )
}

function PlusIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M7 2v10M2 7h10" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
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

function XIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
    </svg>
  )
}

function ComingSoonModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title" onClick={e => e.stopPropagation()}>
        <div className="modal__header">
          <p className="modal__eyebrow">Integrations</p>
          <button className="modal__close" onClick={onClose} aria-label="Close">
            <XIcon />
          </button>
        </div>
        <div className="modal__body">
          <div className="modal__icon-wrap">
            <PlusIcon />
          </div>
          <h2 className="modal__title" id="modal-title">More integrations coming soon</h2>
          <p className="modal__desc">
            We're working on adding Gmail, Notion, and more to your content pipeline. Stay tuned for updates.
          </p>
        </div>
        <div className="modal__footer">
          <button className="btn btn--modal-close" onClick={onClose}>Got it</button>
        </div>
      </div>
    </div>
  )
}

interface IntegrationRowProps {
  logo: React.ReactNode
  name: string
  description: string
  status: 'loading' | 'connected' | 'disconnected'
  meta?: string | undefined
  connectHref?: string | undefined
}

function IntegrationRow({ logo, name, description, status, meta, connectHref }: IntegrationRowProps) {
  return (
    <div className="integration-row">
      <div className="integration-row__logo">{logo}</div>
      <div className="integration-row__body">
        <p className="integration-row__name">{name}</p>
        <p className="integration-row__desc">
          {status === 'loading' ? <span className="skeleton skeleton--text" /> : (meta ?? description)}
        </p>
      </div>
      <div className="integration-row__action">
        {status === 'loading' && <span className="skeleton skeleton--pill" />}
        {status === 'connected' && (
          <span className="badge badge--connected">
            <span className="badge__dot" />
            Connected
          </span>
        )}
        {status === 'disconnected' && connectHref && (
          <a href={connectHref} className="btn btn--connect">
            Connect <ArrowRight />
          </a>
        )}
      </div>
    </div>
  )
}

export default function Settings() {
  const { data: slack, isLoading: slackLoading } = useSlackStatus()
  const { data: linkedin, isLoading: linkedinLoading } = useLinkedInStatus()
  const [modalOpen, setModalOpen] = useState(false)

  const slackMeta = slack?.connected
    ? `${slack.workspace_name ?? 'Workspace'}${slack.channel_count ? ` · ${slack.channel_count} channel${slack.channel_count !== 1 ? 's' : ''} monitored` : ''}`
    : undefined

  return (
    <div className="settings">
      <header className="settings__header">
        <h1 className="settings__title">Settings</h1>
        <p className="settings__subtitle">Manage your workspace integrations and preferences.</p>
      </header>

      <section className="settings__section">
        <div className="settings__section-header">
          <p className="settings__section-label">Integrations</p>
          <button className="btn btn--add" onClick={() => setModalOpen(true)}>
            <PlusIcon /> Add integration
          </button>
        </div>

        <div className="integrations-list">
          <IntegrationRow
            logo={<SlackLogo />}
            name="Slack"
            description="Monitor channels for content signals."
            status={slackLoading ? 'loading' : slack?.connected ? 'connected' : 'disconnected'}
            meta={slackMeta}
            connectHref="/api/oauth/slack/install"
          />
          <IntegrationRow
            logo={<LinkedInLogo />}
            name="LinkedIn"
            description="Authorize posting to your company page."
            status={linkedinLoading ? 'loading' : linkedin?.connected ? 'connected' : 'disconnected'}
            connectHref="/api/oauth/linkedin/install"
          />
        </div>
      </section>

      {modalOpen && <ComingSoonModal onClose={() => setModalOpen(false)} />}
    </div>
  )
}