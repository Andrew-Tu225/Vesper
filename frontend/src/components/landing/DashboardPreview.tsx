import { useState } from 'react'
import styles from './DashboardPreview.module.css'

function QueueIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <path d="M2 4h12M2 8h8M2 12h10" strokeLinecap="round" />
    </svg>
  )
}

function CalIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <rect x="2" y="3" width="12" height="11" rx="2" />
      <path d="M2 7h12M5 1v4M11 1v4" strokeLinecap="round" />
    </svg>
  )
}

function SettingsIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <circle cx="8" cy="8" r="2.5" />
      <path
        d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41M3.05 12.95l1.41-1.41M11.54 4.46l1.41-1.41"
        strokeLinecap="round"
      />
    </svg>
  )
}

function ChevronIcon({ open = false }: { open?: boolean }) {
  return (
    <svg
      className={`${styles.signalChevronIcon}${open ? ` ${styles.signalChevronIconOpen}` : ''}`}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden="true"
    >
      <path d="M4 6l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

type Status = 'in_review' | 'scheduled' | 'posted' | 'approved'
type Panel = 'approve' | 'rewrite' | null

const STATUS_LABELS: Record<Status, string> = {
  in_review: 'In Review',
  scheduled: 'Scheduled',
  approved: 'Approved',
  posted: 'Posted',
}

interface Variant {
  id: string
  label: string
  hook: string
  body: string[]
  hashtags: string[]
  reactions: string
  comments: string
}

interface PreviewSignal {
  id: string
  type: string
  summary: string
  detail: string
  status: Status
  time: string
  variants: Variant[]
}

const PREVIEW_SIGNALS: PreviewSignal[] = [
  {
    id: 'customer-praise',
    type: 'Customer Praise',
    summary: 'TechFlow reported 60% faster onboarding after 3 months - new hires fully productive in week one.',
    detail:
      'We got a message from a customer we had not spoken to in months. They reached out unprompted to say new hires are fully productive in week one, down from nearly three weeks before they switched to our platform.',
    status: 'in_review',
    time: '2h ago',
    variants: [
      {
        id: 'customer-v1',
        label: 'Customer Story',
        hook: 'Vesper Corp',
        body: [
          'We got a message from a customer we had not spoken to in 3 months.',
          'No check-in scheduled. No NPS survey. They just wrote to say their new hires were fully productive in week one.',
          'That is a 60% reduction in onboarding time from where they started before switching to our product.',
          "The best signal is not always a renewal. Sometimes it's a quiet note from a customer telling you the work is working.",
        ],
        hashtags: ['#CustomerSuccess', '#ProductLedGrowth', '#B2BSaaS'],
        reactions: '342 reactions',
        comments: '15 comments',
      },
      {
        id: 'customer-v2',
        label: 'Founder Angle',
        hook: 'Vesper Corp',
        body: [
          'One of my favorite product moments is when a customer writes in without being asked.',
          'This week, TechFlow told us their onboarding time dropped by 60% and new hires were productive in week one.',
          'Not because we nudged them. Not because a success manager asked. Just because they felt the change enough to share it.',
          'That kind of unsolicited proof is what we build for.',
        ],
        hashtags: ['#BuildInPublic', '#CustomerFeedback', '#SaaS'],
        reactions: '217 reactions',
        comments: '9 comments',
      },
    ],
  },
  {
    id: 'product-win',
    type: 'Product Win',
    summary: 'New AI pipeline reduces draft generation from 8 minutes to under 90 seconds end-to-end.',
    detail:
      'The latest release cut end-to-end draft generation from 8 minutes to under 90 seconds. It is the first time the whole workflow feels instant enough for daily use.',
    status: 'scheduled',
    time: '5h ago',
    variants: [
      {
        id: 'product-v1',
        label: 'Launch Post',
        hook: 'Vesper Product',
        body: [
          'We just shipped the fastest version of our drafting workflow yet.',
          'A full signal-to-draft run that used to take 8 minutes now takes under 90 seconds.',
          'That speed changes behavior. Teams do not save sharing for later when the loop feels instant.',
          'More to improve, but this one feels important.',
        ],
        hashtags: ['#ProductUpdate', '#AIWorkflow', '#B2B'],
        reactions: '128 reactions',
        comments: '6 comments',
      },
      {
        id: 'product-v2',
        label: 'Ops Angle',
        hook: 'Vesper Product',
        body: [
          'Internal benchmark from this week: draft generation is now under 90 seconds end-to-end.',
          'That sounds like a speed stat, but the real win is consistency. Teams are reviewing and posting more often because the queue never feels blocked.',
        ],
        hashtags: ['#ProductOps', '#ContentSystems'],
        reactions: '84 reactions',
        comments: '4 comments',
      },
    ],
  },
  {
    id: 'founder-insight',
    type: 'Founder Insight',
    summary: 'The hiring pipeline shifts dramatically when candidates can actually see your LinkedIn presence.',
    detail:
      'When people can see a steady stream of thoughtful product and customer stories, they understand the company before the first interview. That changes who raises their hand.',
    status: 'approved',
    time: '1d ago',
    variants: [
      {
        id: 'founder-v1',
        label: 'Hiring Insight',
        hook: 'Founder note',
        body: [
          'Your hiring pipeline changes when candidates can actually see what your team is building.',
          'A steady stream of product lessons and customer stories does more than help sales. It gives future teammates a reason to believe before the first interview.',
          'Visibility compounds.',
        ],
        hashtags: ['#Hiring', '#Brand', '#Startup'],
        reactions: '191 reactions',
        comments: '11 comments',
      },
      {
        id: 'founder-v2',
        label: 'Brand POV',
        hook: 'Founder note',
        body: [
          'A quiet company looks smaller than it is.',
          'When teams publish consistently, candidates, customers, and partners stop guessing who you are. They can see the work in public.',
        ],
        hashtags: ['#CompanyBuilding', '#Brand'],
        reactions: '73 reactions',
        comments: '3 comments',
      },
    ],
  },
]

function SignalCard({
  signal,
  expanded,
  panel,
  onToggle,
  onPanelChange,
}: {
  signal: PreviewSignal
  expanded: boolean
  panel: Panel
  onToggle: () => void
  onPanelChange: (panel: Panel) => void
}) {
  const [activeVariantId, setActiveVariantId] = useState(signal.variants[0]?.id ?? '')
  const activeVariant =
    signal.variants.find((variant) => variant.id === activeVariantId) ?? signal.variants[0]

  return (
    <div className={`${styles.signalCard}${expanded ? ` ${styles.signalCardExpanded}` : ''}`}>
      <div
        className={styles.signalCardHeader}
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        onClick={onToggle}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            onToggle()
          }
        }}
      >
        <span className={styles.signalTypeLabel}>{signal.type}</span>
        <span className={styles.signalSummary}>{signal.summary}</span>
        <div className={styles.signalMeta}>
          <span className={`${styles.statusBadge} ${styles[`status_${signal.status}`]}`}>
            <span className={styles.statusDot} />
            {STATUS_LABELS[signal.status]}
          </span>
          <span className={styles.signalTime}>{signal.time}</span>
          <span className={styles.signalChevron}>
            <ChevronIcon open={expanded} />
          </span>
        </div>
      </div>

      {expanded && (
        <div className={styles.signalCardBody}>
          <p className={styles.signalSummaryFull}>{signal.detail}</p>

          <div className={styles.variantTabs}>
            {signal.variants.map((variant) => (
              <button
                key={variant.id}
                className={`${styles.variantTab}${activeVariant.id === variant.id ? ` ${styles.variantTabActive}` : ''}`}
                onClick={(e) => {
                  e.stopPropagation()
                  setActiveVariantId(variant.id)
                }}
              >
                {variant.label}
              </button>
            ))}
          </div>

          <div className={styles.linkedinPost}>
            <div className={styles.linkedinHeader}>
              <div className={styles.linkedinAvatar}>VC</div>
              <div className={styles.linkedinMeta}>
                <div className={styles.linkedinAuthorRow}>
                  <span className={styles.linkedinAuthor}>{activeVariant.hook}</span>
                  <button className={styles.linkedinFollow}>+ Follow</button>
                </div>
                <div className={styles.linkedinSubmeta}>Software - 1,247 followers</div>
                <div className={styles.linkedinSubmeta}>Just now - Public</div>
              </div>
            </div>

            <div className={styles.linkedinBody}>
              {activeVariant.body.map((paragraph) => (
                <p key={paragraph}>{paragraph}</p>
              ))}
              <p className={styles.linkedinTags}>{activeVariant.hashtags.join(' ')}</p>
            </div>

            <div className={styles.linkedinStats}>
              <span>👍 ❤️ 🔥</span>
              <span>{activeVariant.reactions}</span>
              <span>{activeVariant.comments}</span>
            </div>

            <div className={styles.linkedinActions}>
              <span>Like</span>
              <span>Comment</span>
              <span>Repost</span>
              <span>Send</span>
            </div>
          </div>

          {panel === 'approve' && (
            <div className={styles.inlinePanel}>
              <span className={styles.inlinePanelLabel}>Schedule for</span>
              <div className={styles.inlinePanelRow}>
                <div className={styles.fakeInput}>Tomorrow, 9:00 AM</div>
                <button className={styles.panelGhostBtn}>Cancel</button>
                <button className={styles.panelPrimaryBtn}>Confirm</button>
              </div>
            </div>
          )}

          {panel === 'rewrite' && (
            <div className={styles.inlinePanel}>
              <span className={styles.inlinePanelLabel}>Rewrite feedback</span>
              <div className={styles.fakeTextarea}>
                Make it shorter, more casual, and lead with the onboarding outcome.
              </div>
              <div className={styles.inlinePanelRow}>
                <button className={styles.panelGhostBtn}>Cancel</button>
                <button className={styles.panelSecondaryBtn}>Request rewrite</button>
                <span className={styles.charCount}>68/500</span>
              </div>
            </div>
          )}

          {signal.status === 'scheduled' && (
            <div className={styles.scheduledInfo}>Scheduled for Apr 28, 9:00 AM</div>
          )}

          <div className={styles.signalActions}>
            <button
              className={styles.actionPrimary}
              onClick={(e) => {
                e.stopPropagation()
                onPanelChange(panel === 'approve' ? null : 'approve')
              }}
            >
              {panel === 'approve' ? 'Cancel approve' : 'Approve'}
            </button>
            <button
              className={styles.actionSecondary}
              onClick={(e) => {
                e.stopPropagation()
                onPanelChange(panel === 'rewrite' ? null : 'rewrite')
              }}
            >
              {panel === 'rewrite' ? 'Cancel rewrite' : 'Rewrite'}
            </button>
            <button className={styles.actionGhost}>Reject</button>
          </div>
        </div>
      )}
    </div>
  )
}

export function DashboardPreview() {
  const [expandedId, setExpandedId] = useState<string>('customer-praise')
  const [panel, setPanel] = useState<Panel>(null)

  return (
    <section className={styles.section}>
      <div className={styles.inner}>
        <p className={styles.eyebrow} data-reveal>
          The Vesper workspace
        </p>
        <h2 className={styles.title} data-reveal data-delay="1">
          One place for every signal,
          <br />
          <em className={styles.titleAccent}>draft, and decision.</em>
        </h2>

        <div className={styles.previewStage} data-reveal data-delay="2">
          <div className={styles.browserOuter}>
            <div className={styles.chrome}>
              <div className={styles.chromeDots}>
                <span style={{ background: '#ff5f57' }} />
                <span style={{ background: '#ffbd2e' }} />
                <span style={{ background: '#28c840' }} />
              </div>
              <div className={styles.chromeUrl}>app.vesper.ai/queue</div>
            </div>

            <div className={styles.appShell}>
              <aside className={styles.sidebar}>
                <div className={styles.sidebarBrand}>
                  <img src="/logo.svg" alt="Vesper" height="26" />
                  <span className={styles.workspaceName}>Acme Corp</span>
                </div>

                <nav className={styles.sidebarNav}>
                  <div className={styles.navSection}>
                    <span className={styles.navSectionLabel}>Workspace</span>
                    <div className={`${styles.navItem} ${styles.navItemActive}`}>
                      <QueueIcon /> Queue
                      <span className={styles.navBadge}>3</span>
                    </div>
                    <div className={styles.navItem}>
                      <CalIcon /> Calendar
                    </div>
                    <div className={styles.navItem}>
                      <SettingsIcon /> Settings
                    </div>
                  </div>

                  <div className={styles.navDivider} />

                  <div className={styles.navSection}>
                    <span className={styles.navSectionLabel}>Channels</span>
                    <div className={styles.channelRow}>
                      <span className={styles.channelPulse} />
                      <span className={styles.channelName}>#wins-and-shoutouts</span>
                    </div>
                    <div className={styles.channelRow}>
                      <span className={styles.channelPulse} />
                      <span className={styles.channelName}>#general</span>
                    </div>
                    <div className={styles.channelRow}>
                      <span className={`${styles.channelPulse} ${styles.channelPulseGray}`} />
                      <span className={styles.channelName}>#product-updates</span>
                    </div>
                  </div>
                </nav>
              </aside>

              <div className={styles.main}>
                <div className={styles.topbar}>
                  <span className={styles.pageTitle}>Queue</span>
                  <div className={styles.topbarRight}>
                    <span className={styles.pendingBadge}>3 pending review</span>
                    <button className={styles.newSignalBtn}>+ New Signal</button>
                  </div>
                </div>

                <div className={styles.statBanner}>
                  <div className={styles.statItem}>
                    <span className={styles.statNumber}>14</span>
                    <span className={styles.statLabel}>signals this week</span>
                  </div>
                  <div className={styles.statDivider} />
                  <div className={styles.statItem}>
                    <span className={styles.statNumber}>3</span>
                    <span className={styles.statLabel}>pending review</span>
                  </div>
                  <div className={styles.statDivider} />
                  <div className={styles.statItem}>
                    <span className={styles.statNumber}>2</span>
                    <span className={styles.statLabel}>scheduled</span>
                  </div>
                  <div className={styles.statDivider} />
                  <div className={styles.statItem}>
                    <span className={styles.statNumber}>9</span>
                    <span className={styles.statLabel}>posted this month</span>
                  </div>
                </div>

                <div className={styles.content}>
                  <div className={styles.filterTabs}>
                    {['All', 'In Review', 'Scheduled', 'Approved', 'Posted'].map((t) => (
                      <span
                        key={t}
                        className={`${styles.filterTab}${t === 'In Review' ? ` ${styles.filterTabActive}` : ''}`}
                      >
                        {t}
                      </span>
                    ))}
                  </div>

                  <div className={styles.signalList}>
                    {PREVIEW_SIGNALS.map((signal) => (
                      <SignalCard
                        key={signal.id}
                        signal={signal}
                        expanded={expandedId === signal.id}
                        panel={expandedId === signal.id ? panel : null}
                        onToggle={() => {
                          if (expandedId === signal.id) {
                            setExpandedId('')
                            setPanel(null)
                          } else {
                            setExpandedId(signal.id)
                            setPanel(null)
                          }
                        }}
                        onPanelChange={(nextPanel) => setPanel(nextPanel)}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className={styles.labels} data-reveal data-delay="3">
          <span>Approval queue</span>
          <span className={styles.labelDot}>·</span>
          <span>Content calendar</span>
          <span className={styles.labelDot}>·</span>
          <span>Channel monitoring</span>
        </div>
      </div>
    </section>
  )
}
