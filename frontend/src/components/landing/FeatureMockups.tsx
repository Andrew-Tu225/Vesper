import styles from '../../pages/landing.module.css'

function ThumbsUpIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.35" aria-hidden="true">
      <path d="M6.5 7V4.6a2.1 2.1 0 0 1 2.1-2.1l.3.1v3.5h3a1.5 1.5 0 0 1 1.5 1.7l-.6 4a1.5 1.5 0 0 1-1.5 1.2H6.5V7Z" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M3 7h2.5v6H3.7A.7.7 0 0 1 3 12.3V7Z" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function CommentIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.35" aria-hidden="true">
      <path d="M3.3 3.5h9.4c.7 0 1.3.6 1.3 1.3v5.3c0 .7-.6 1.3-1.3 1.3H7l-3.1 2V4.8c0-.7.6-1.3 1.4-1.3Z" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function RepostIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.35" aria-hidden="true">
      <path d="M5.5 3H12v6.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="m10.4 7.1 1.6 2.4 2.4-1.6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M10.5 13H4V6.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5.6 8.9 4 6.5 1.6 8.1" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function SendIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.35" aria-hidden="true">
      <path d="m14 2-12 5.2 4.5 1.4L7.9 14 14 2Z" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M6.5 8.6 14 2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

type MockupTone = 'hero' | 'tile'

interface SharedProps {
  tone?: MockupTone
  className?: string | undefined
}

function mockupClass(tone: MockupTone, className?: string) {
  return [
    styles.productMockup,
    tone === 'hero' ? styles.productMockupHero : styles.productMockupTile,
    className,
  ]
    .filter(Boolean)
    .join(' ')
}

export function LinkedInPostMockup({ tone = 'tile', className }: SharedProps) {
  return (
    <div className={mockupClass(tone, className)}>
      <div className={`${styles.productMockupShell} ${styles.linkedinPostMockup}`}>
        <div className={styles.linkedinPostHeader}>
          <div className={styles.linkedinPostAvatar}>VC</div>
          <div className={styles.linkedinPostMeta}>
            <strong>Vesper Corp</strong>
            <span>Software · 1,247 followers</span>
            <span>Just now · Public</span>
          </div>
          <button className={styles.linkedinFollowPill}>+ Follow</button>
        </div>

        <div className={styles.linkedinPostBody}>
          <p>
            Last week, a customer we had not spoken to in months reached out without a prompt.
          </p>
          <p>
            They told us new hires were now <strong>fully productive in their first week</strong>,
            down from nearly three weeks before they switched to our platform.
          </p>
          <p>
            That is a <strong>60% reduction in onboarding time</strong>. No survey. No check-in.
            Just a customer going out of their way to say it is working.
          </p>
          <p className={styles.linkedinPostTags}>#CustomerSuccess #B2BSaaS #Onboarding #ProductLed</p>
        </div>

        <div className={styles.linkedinPostStats}>
          <span className={styles.linkedinEmojiRow}>
            <span>👍</span>
            <span>❤️</span>
            <span>🔥</span>
          </span>
          <span>342 reactions</span>
          <span>28 reposts</span>
          <span>15 comments</span>
        </div>

        <div className={styles.linkedinPostActions}>
          <button><ThumbsUpIcon />Like</button>
          <button><CommentIcon />Comment</button>
          <button><RepostIcon />Repost</button>
          <button><SendIcon />Send</button>
        </div>
      </div>
    </div>
  )
}

export function SlackChannelMockup({ tone = 'tile', className }: SharedProps) {
  return (
    <div className={mockupClass(tone, className)}>
      <div className={`${styles.productMockupShell} ${styles.slackChannelMockup}`}>
        <div className={styles.slackDesktopShell}>
          <aside className={styles.slackSidebarMini}>
            <div className={styles.slackSidebarTopRow}>
              <div className={styles.slackSidebarBadge}>V</div>
              <div className={styles.slackSidebarWorkspace}>Vesper Corp</div>
            </div>
            <div className={styles.slackSidebarSection}>
              <span># general</span>
              <span className={styles.slackSidebarActive}># wins-and-shoutouts</span>
              <span># product-updates</span>
              <span># design</span>
            </div>
          </aside>

          <div className={styles.slackChannelMain}>
            <div className={styles.slackChannelToolbar}>
              <div className={styles.slackWindowDots}>
                <span />
                <span />
                <span />
              </div>
              <span className={styles.slackWindowLabel}># wins-and-shoutouts</span>
            </div>

            <div className={styles.slackChannelHeader}>
              <div>
                <strong># wins-and-shoutouts</strong>
                <span>12 members</span>
              </div>
            </div>

            <div className={styles.slackChannelMessages}>
              <div className={styles.slackMessageRow}>
                <div className={`${styles.slackMessageAvatar} ${styles.slackMessageAvatarRose}`}>SK</div>
                <div className={styles.slackMessageContent}>
                  <div className={styles.slackMessageMeta}>
                    <strong>Sarah Kim</strong>
                    <span>2:31 PM</span>
                  </div>
                  <p>
                    Just wrapped a call with TechFlow — 3 months in and their onboarding time
                    dropped 60%! 🚀
                  </p>
                  <div className={styles.slackReactionRow}>
                    <span>🎉 6</span>
                    <span>🎉 14</span>
                  </div>
                </div>
              </div>

              <div className={styles.slackMessageRow}>
                <div className={`${styles.slackMessageAvatar} ${styles.slackMessageAvatarBlue}`}>MJ</div>
                <div className={styles.slackMessageContent}>
                  <div className={styles.slackMessageMeta}>
                    <strong>Marcus J.</strong>
                    <span>2:32 PM</span>
                  </div>
                  <p>
                    That's incredible!! Did they share specifics? 👀
                  </p>
                </div>
              </div>

              <div className={`${styles.slackMessageRow} ${styles.slackMessageRowReply}`}>
                <div className={`${styles.slackMessageAvatar} ${styles.slackMessageAvatarRose}`}>SK</div>
                <div className={styles.slackMessageContent}>
                  <div className={styles.slackMessageMeta}>
                    <strong>Sarah Kim</strong>
                    <span>2:33 PM</span>
                  </div>
                  <p>
                    Yeah — new employees fully productive week 1. They reached out unprompted
                    to tell us 🙌
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export function SlackApprovalMockup({ tone = 'tile', className }: SharedProps) {
  return (
    <div className={mockupClass(tone, className)}>
      <div className={`${styles.productMockupShell} ${styles.slackApprovalMockup}`}>
        <div className={styles.slackWindowBar}>
          <div className={styles.slackWindowDots}>
            <span />
            <span />
            <span />
          </div>
          <span className={styles.slackWindowLabel}># social-queue</span>
        </div>

        <div className={styles.approvalCard}>
          <div className={styles.approvalCardHeader}>
            <div className={styles.approvalCardTitle}>
              <span className={styles.approvalCardBot}>V</span>
              <div>
                <strong>Vesper draft ready</strong>
                <span>Approval required before publish</span>
              </div>
            </div>
            <span className={styles.approvalCardState}>Pending</span>
          </div>

          <div className={styles.approvalDraftBlock}>
            <p>
              "Style Library v2 is live. The system now learns from every approved post and
              suggested hooks are noticeably tighter after a week of usage..."
            </p>
            <div className={styles.approvalDraftMeta}>
              <span>LinkedIn</span>
              <span>product_update</span>
              <span>214 words</span>
            </div>
          </div>

          <div className={styles.approvalActions}>
            <button className={styles.approvalPrimary}>Approve</button>
            <button>Schedule</button>
            <button>Rewrite</button>
          </div>
        </div>
      </div>
    </div>
  )
}

const CLASSIFY_ROWS = [
  { label: 'customer_praise', pct: '94%', width: '94%' },
  { label: 'product_win', pct: '62%', width: '62%' },
  { label: 'founder_insight', pct: '24%', width: '24%' },
]

export function ClassifySignalMockup({ tone = 'tile', className }: SharedProps) {
  return (
    <div className={mockupClass(tone, className)}>
      <div className={`${styles.productMockupShell} ${styles.secondaryMockup}`}>
        <div className={styles.secondaryMockupHeader}>
          <strong>Signal processing</strong>
          <span>customer_win</span>
        </div>
        <blockquote className={styles.secondaryQuote}>
          "Just wrapped a call with TechFlow — 3 months in and onboarding time dropped 60%."
        </blockquote>
        <div className={styles.classifyList}>
          {CLASSIFY_ROWS.map((row) => (
            <div key={row.label} className={styles.classifyListRow}>
              <span>{row.label}</span>
              <div className={styles.classifyListBar}>
                <div className={styles.classifyListBarFill} style={{ width: row.width }} />
              </div>
              <strong>{row.pct}</strong>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export function RedactionMockup({ tone = 'tile', className }: SharedProps) {
  return (
    <div className={mockupClass(tone, className)}>
      <div className={`${styles.productMockupShell} ${styles.secondaryMockup}`}>
        <div className={styles.secondaryMockupHeader}>
          <strong>Pre-draft redaction</strong>
          <span>before generation</span>
        </div>
        <div className={styles.redactionColumns}>
          <div>
            <label>Before</label>
            <p>
              TechFlow&apos;s onboarding dropped 60%. Sarah Kim said their Q2 numbers rose by
              $240K.
            </p>
          </div>
          <div>
            <label>After</label>
            <p>
              <span>[CLIENT]</span> onboarding dropped <span>[X%]</span>. <span>[NAME]</span> shared
              their <span>[PERIOD]</span> numbers were up <span>[AMOUNT]</span>.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
