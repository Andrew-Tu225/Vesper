import React, { useState, useRef, useCallback, useEffect } from 'react'
import styles from './landing.module.css'

// ─── Icons ──────────────────────────────────────────────────────────────────
function ArrowRight() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function SparkleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M8 1L9.8 6.2L15 8L9.8 9.8L8 15L6.2 9.8L1 8L6.2 6.2L8 1Z" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
      <path d="M2 6.5L5 9.5L11 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

// ─── Feature SVG icons (stroke, 22px, dark-section safe) ─────────────────────
function IconBroadcast() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" aria-hidden="true">
      <path d="M5 12.5c0-3.87 3.13-7 7-7s7 3.13 7 7" />
      <path d="M8 12.5c0-2.21 1.79-4 4-4s4 1.79 4 4" />
      <circle cx="12" cy="12.5" r="1.5" fill="currentColor" stroke="none" />
    </svg>
  )
}

function IconFilter() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" aria-hidden="true">
      <path d="M4 6h16M7 12h10M10 18h4" />
    </svg>
  )
}

function IconShield() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3L4 6.5v5.5c0 5 3.5 8.5 8 10 4.5-1.5 8-5 8-10V6.5L12 3z" />
    </svg>
  )
}

function IconDocument() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M14 3H6a2 2 0 00-2 2v14a2 2 0 002 2h12a2 2 0 002-2V9l-6-6z" />
      <path d="M14 3v6h6M8 13h8M8 17h5" />
    </svg>
  )
}

function IconCalendar() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" aria-hidden="true">
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M3 10h18M8 3v4M16 3v4" />
    </svg>
  )
}

function IconRefresh() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 12a8 8 0 018-8 8 8 0 016.93 4" />
      <path d="M20 4v4h-4" />
      <path d="M20 12a8 8 0 01-8 8 8 8 0 01-6.93-4" />
      <path d="M4 20v-4h4" />
    </svg>
  )
}

// ─── Typewriter hero component ────────────────────────────────────────────────
const TYPEWRITER_PHRASES = [
  'customer feedback',
  'product updates',
  'company milestones',
  'founder insights',
  'team achievements',
]

function TypewriterWord() {
  const [displayText, setDisplayText] = useState('')
  const [phraseIndex, setPhraseIndex] = useState(0)
  const [isDeleting, setIsDeleting] = useState(false)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    const current = TYPEWRITER_PHRASES[phraseIndex] ?? ''
    // Always clear the previous pending tick before scheduling a new one
    if (timeoutRef.current) clearTimeout(timeoutRef.current)

    if (!isDeleting && displayText === current) {
      // Fully typed — pause, then begin deleting
      timeoutRef.current = setTimeout(() => setIsDeleting(true), 1800)
    } else if (!isDeleting) {
      // Still typing character by character
      timeoutRef.current = setTimeout(() => {
        setDisplayText(current.slice(0, displayText.length + 1))
      }, 75)
    } else if (displayText === '') {
      // Fully deleted — batch both state updates so they fire in one render,
      // preventing the old phrase from re-typing before phraseIndex updates
      timeoutRef.current = setTimeout(() => {
        setIsDeleting(false)
        setPhraseIndex((i) => (i + 1) % TYPEWRITER_PHRASES.length)
      }, 320)
    } else {
      // Still deleting character by character
      timeoutRef.current = setTimeout(() => {
        setDisplayText((t) => t.slice(0, -1))
      }, 45)
    }

    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
    }
  }, [displayText, isDeleting, phraseIndex])

  return (
    // inline-grid + ::after ghost text keeps the box a fixed width equal
    // to the longest phrase, so "Transform" and line 2 never shift position
    <span className={styles.typewriterWord}>
      <span className={styles.typewriterText}>
        {displayText}
        <span className={styles.caret} aria-hidden="true" />
      </span>
    </span>
  )
}

// ─── Scroll reveal hook ───────────────────────────────────────────────────────
function useScrollReveal() {
  useEffect(() => {
    const els = document.querySelectorAll('[data-reveal]')
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('revealed')
            observer.unobserve(entry.target)
          }
        })
      },
      { threshold: 0.12, rootMargin: '0px 0px -48px 0px' }
    )
    els.forEach((el) => observer.observe(el))
    return () => observer.disconnect()
  }, [])
}

// ─── Hero Visual — animated Slack → LinkedIn transformation ──────────────────
const MSG2_FULL = "That's incredible!! Did they share specifics? 👀"
const MSG3_FULL = "Yeah — new employees fully productive week 1. They reached out unprompted to tell us 🙌"

function HeroVisual() {
  const [msg2Len, setMsg2Len] = useState(0)
  const [msg3Len, setMsg3Len] = useState(0)
  const [bridgeStage, setBridgeStage] = useState(0)
  const [linkedinVisible, setLinkedinVisible] = useState(false)
  const [cycle, setCycle] = useState(0)

  useEffect(() => {
    const cleanup: Array<() => void> = []

    function addTimer(fn: () => void, delay: number) {
      const id = setTimeout(fn, delay)
      cleanup.push(() => clearTimeout(id))
    }

    function addInterval(fn: () => void, ms: number): ReturnType<typeof setInterval> {
      const id = setInterval(fn, ms)
      cleanup.push(() => clearInterval(id))
      return id
    }

    addTimer(() => {
      let i = 0
      const iv = addInterval(() => { i++; setMsg2Len(i); if (i >= MSG2_FULL.length) clearInterval(iv) }, 38)
    }, 2000)

    addTimer(() => {
      let j = 0
      const iv = addInterval(() => { j++; setMsg3Len(j); if (j >= MSG3_FULL.length) clearInterval(iv) }, 30)
    }, 5500)

    addTimer(() => setBridgeStage(1), 8500)
    addTimer(() => setBridgeStage(2), 9400)
    addTimer(() => setBridgeStage(3), 10300)
    addTimer(() => setLinkedinVisible(true), 11000)
    addTimer(() => {
      setMsg2Len(0); setMsg3Len(0); setBridgeStage(0); setLinkedinVisible(false)
      setCycle(c => c + 1)
    }, 16500)

    return () => cleanup.forEach(fn => fn())
  }, [cycle])

  return (
    <div className={styles.heroVisual}>
      {/* ── Slack Card ── */}
      <div className={styles.slackCard}>
        <div className={styles.slackWorkspaceBar}>
          <div className={styles.slackWorkspaceIcon}>V</div>
          <span className={styles.slackWorkspaceName}>Vesper Corp</span>
          <svg className={styles.slackWorkspaceChevron} width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
            <path d="M2 4l3 3 3-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </div>
        <div className={styles.slackCardInner}>
          <div className={styles.slackSidebar}>
            <p className={styles.slackSidebarLabel}>Channels</p>
            <div className={styles.slackChannelItem}><span>#</span>general</div>
            <div className={`${styles.slackChannelItem} ${styles.slackChannelActive}`}><span>#</span>wins-and-shoutouts</div>
            <div className={styles.slackChannelItem}><span>#</span>product-updates</div>
            <div className={styles.slackChannelItem}><span>#</span>design</div>
          </div>
          <div className={styles.slackMain}>
            <div className={styles.slackHeader}>
              <div className={styles.slackDots}><span /><span /><span /></div>
              <span className={styles.slackChannel}># wins-and-shoutouts</span>
              <span className={styles.slackMemberCount}>12 members</span>
            </div>
            <div className={styles.slackMessages}>
              <div className={styles.slackMsg}>
                <div className={`${styles.slackAvatar} ${styles.slackAvatarRed}`}>SK</div>
                <div className={styles.slackMsgRight}>
                  <div className={styles.slackMsgMeta}><strong>Sarah Kim</strong><span>2:31 PM</span></div>
                  <p className={styles.slackMsgText}>Just wrapped a call with TechFlow — 3 months in and their onboarding time dropped 60%! 🚀</p>
                  <div className={styles.slackReactions}>
                    <span className={styles.slackReaction}>🚀 6</span>
                    <span className={styles.slackReaction}>🎉 14</span>
                  </div>
                </div>
              </div>
              {msg2Len > 0 && (
                <div className={styles.slackMsg}>
                  <div className={`${styles.slackAvatar} ${styles.slackAvatarBlue}`}>MJ</div>
                  <div className={styles.slackMsgRight}>
                    <div className={styles.slackMsgMeta}><strong>Marcus J.</strong><span>2:32 PM</span></div>
                    <p className={styles.slackMsgText}>
                      {MSG2_FULL.slice(0, msg2Len)}{msg2Len < MSG2_FULL.length && <span className={styles.slackTypingCaret} />}
                    </p>
                  </div>
                </div>
              )}
              {msg3Len > 0 && (
                <div className={styles.slackMsg}>
                  <div className={`${styles.slackAvatar} ${styles.slackAvatarRed}`}>SK</div>
                  <div className={styles.slackMsgRight}>
                    <div className={styles.slackMsgMeta}><strong>Sarah Kim</strong><span>2:33 PM</span></div>
                    <p className={styles.slackMsgText}>
                      {MSG3_FULL.slice(0, msg3Len)}{msg3Len < MSG3_FULL.length && <span className={styles.slackTypingCaret} />}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ── Transform Bridge ── */}
      <div className={styles.transformBridge}>
        <div className={styles.bridgeTrackWrap}>
          <div className={styles.bridgeTrack} />
          <div className={`${styles.bridgeParticle} ${bridgeStage >= 1 ? styles.bridgeParticleOn : ''}`} />
          <div className={`${styles.bridgeParticle} ${bridgeStage >= 1 ? styles.bridgeParticleOn : ''}`} style={{ animationDelay: '0.45s' }} />
          <div className={`${styles.bridgeParticle} ${bridgeStage >= 1 ? styles.bridgeParticleOn : ''}`} style={{ animationDelay: '0.9s' }} />
        </div>
        <div className={`${styles.transformBadge} ${bridgeStage >= 1 ? styles.transformBadgeActive : ''}`}>
          <SparkleIcon /> Vesper AI
        </div>
        <div className={styles.bridgeStages}>
          <span className={`${styles.bridgePill} ${bridgeStage >= 1 ? styles.bridgePillLit : ''}`}>Classify</span>
          <span className={styles.bridgeArrow}>›</span>
          <span className={`${styles.bridgePill} ${bridgeStage >= 2 ? styles.bridgePillLit : ''}`}>Draft</span>
          <span className={styles.bridgeArrow}>›</span>
          <span className={`${styles.bridgePill} ${bridgeStage >= 3 ? styles.bridgePillDone : ''}`}>{bridgeStage >= 3 ? '✓ Ready' : 'Ready'}</span>
        </div>
      </div>

      {/* ── LinkedIn Card ── */}
      <div className={`${styles.linkedinCard} ${linkedinVisible ? styles.linkedinCardIn : ''}`}>
        <div className={styles.linkedinHeader}>
          <div className={styles.linkedinAvatar}>VC</div>
          <div className={styles.linkedinMeta}>
            <strong>Vesper Corp</strong>
            <span>Software · 1,247 followers</span>
            <span className={styles.linkedinTime}>Just now · 🌍</span>
          </div>
          <button className={styles.linkedinFollowBtn}>+ Follow</button>
        </div>
        <div className={styles.linkedinBody}>
          <p className={styles.linkedinText}>
            We got a message last week from a customer we hadn't spoken to in 3 months.<br /><br />
            No check-in scheduled. No NPS survey nudging them. They just wrote to tell us that
            their new hires are <strong>fully productive in their first week on the job</strong> — down
            from three weeks before they switched to our platform.<br /><br />
            That's a <strong>60% reduction in onboarding time</strong>. Unprompted.<br /><br />
            I've been in B2B long enough to know that the best signal isn't a renewal or an
            upsell. It's the message a customer sends when nobody asked. When they just want
            you to know it's working.<br /><br />
            That's what we're building toward. Every release, every iteration.<br /><br />
            <span className={styles.linkedinTags}>#CustomerSuccess #ProductLed #B2BSaaS #Onboarding</span>
          </p>
        </div>
        <div className={styles.linkedinReactionBar}>
          <span className={styles.linkedinEmojiStack}>👍❤️🔥</span>
          <span>342 reactions · 28 reposts · 15 comments</span>
        </div>
        <div className={styles.linkedinActionBar}>
          <button className={styles.linkedinActionBtn}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M14 9V5a3 3 0 00-3-3l-4 9v11h11.28a2 2 0 002-1.7l1.38-9a2 2 0 00-2-2.3H14z"/></svg>Like
          </button>
          <button className={styles.linkedinActionBtn}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>Comment
          </button>
          <button className={styles.linkedinActionBtn}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M17 1l4 4-4 4M3 11V9a4 4 0 014-4h14M7 23l-4-4 4-4M21 13v2a4 4 0 01-4 4H3"/></svg>Repost
          </button>
          <button className={styles.linkedinActionBtn}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>Send
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Navbar ───────────────────────────────────────────────────────────────────
function Navbar({ onCTA }: { onCTA: () => void }) {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <nav className={styles.nav}>
      <div className={styles.navInner}>
        <div className={styles.navLogo}>
          <a href="/">
            <img src="/logo.svg" alt="Vesper" height="56" />
          </a>
        </div>
        <div className={styles.navLinks}>
          <a href="#how-it-works" className={styles.navLink}>How it works</a>
          <a href="#features" className={styles.navLink}>Features</a>
          <a href="#waitlist" className={styles.navLink}>Early access</a>
        </div>
        <button className={styles.navCta} onClick={onCTA}>
          Join Waitlist
        </button>
        <button
          className={styles.navHamburger}
          onClick={() => setMenuOpen(o => !o)}
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={menuOpen}
        >
          <span className={`${styles.hamburgerLine} ${menuOpen ? styles.hamburgerLineTopOpen : ''}`} />
          <span className={`${styles.hamburgerLine} ${menuOpen ? styles.hamburgerLineMidOpen : ''}`} />
          <span className={`${styles.hamburgerLine} ${menuOpen ? styles.hamburgerLineBotOpen : ''}`} />
        </button>
      </div>
      {menuOpen && (
        <div className={styles.mobileMenu}>
          <a href="#how-it-works" className={styles.mobileMenuLink} onClick={() => setMenuOpen(false)}>How it works</a>
          <a href="#features" className={styles.mobileMenuLink} onClick={() => setMenuOpen(false)}>Features</a>
          <a href="#waitlist" className={styles.mobileMenuLink} onClick={() => setMenuOpen(false)}>Early access</a>
          <button className={styles.mobileMenuCta} onClick={() => { setMenuOpen(false); onCTA() }}>
            Join Waitlist
          </button>
        </div>
      )}
    </nav>
  )
}

// ─── Hero ────────────────────────────────────────────────────────────────────
function HeroSection({ onCTA }: { onCTA: () => void }) {
  return (
    <section className={styles.hero}>
      {/* Centered copy block */}
      <div className={styles.heroContent}>
        <div className={styles.heroBadge}>
          <span className={styles.heroBadgePulse} />
          AI-powered content intelligence
        </div>

        <h1 className={styles.heroTitle}>
          Transform <TypewriterWord /><br />
          into LinkedIn Stories
        </h1>

        <p className={styles.heroSub}>
          A complete workflow that monitors your workspace, classifies what's worth sharing,
          and routes AI-drafted posts through your approval queue automatically.
        </p>

        <div className={styles.heroCtas}>
          <button className={styles.heroCta} onClick={onCTA}>
            Join Waitlist<ArrowRight />
          </button>
          <a href="#how-it-works" className={styles.heroSecondary}>
            See how it works
          </a>
        </div>

        <div className={styles.heroProof}>
          <span className={styles.heroProofItem}><CheckIcon /> Try one month for free</span>
          <span className={styles.heroProofItem}><CheckIcon /> Integrates with existing Slack</span>
          <span className={styles.heroProofItem}><CheckIcon /> 100% approval-gated</span>
        </div>
      </div>

      <HeroVisual />
    </section>
  )
}

// ─── Problem Section ─────────────────────────────────────────────────────────
function ProblemSection() {
  return (
    <section className={styles.problem}>
      <div className={styles.problemInner}>
        <p className={styles.problemEyebrow} data-reveal>The problem</p>

        <p className={styles.problemLead} data-reveal data-delay="1">
          Your company is producing content signals every single day. None of it is reaching your audience.
        </p>

        <div className={styles.problemBody}>
          <p data-reveal data-delay="1">
            Customer wins land in <strong>#wins-and-shoutouts</strong>. Product milestones get
            announced in <strong>#general</strong>. Founder observations get shared in DMs, then
            scroll out of view within hours. Each one is genuinely worth publishing. Each one is
            forgotten by the time anyone thinks to write a post.
          </p>
          <p data-reveal data-delay="2">
            You know LinkedIn matters. Your potential clients are on it. Your recruiting pipeline
            depends on it. Your competitors are building audiences while your team's best insights
            sit unreachable behind a notification badge.
          </p>
          <p data-reveal data-delay="3">
            So content becomes a backlog item. Posts get half-drafted and abandoned. Customer stories
            go unshared. Hiring announcements miss the moment. And the gap between what your company
            does and what the world knows about it keeps widening — not because the stories aren't
            there, but because no one has the bandwidth to capture them consistently.
          </p>
        </div>

        <p className={styles.problemInsight} data-reveal>
          The bottleneck isn't content strategy.<br />
          <em>It's that no system is watching.</em>
        </p>
        <p className={styles.problemSolution} data-reveal data-delay="1">
          Vesper is that system. It monitors your communication workspace continuously, classifies
          what's worth amplifying, and delivers ready-to-approve drafts to your team — without
          adding a single item to anyone's to-do list.
        </p>
      </div>
    </section>
  )
}

// ─── Trust Strip ─────────────────────────────────────────────────────────────
function TrustStrip() {
  return (
    <div className={styles.trust}>
      <p className={styles.trustLabel} data-reveal>Measured outcomes from early teams</p>
      <div className={styles.trustStats}>
        <div className={styles.trustStat} data-reveal data-delay="1">
          <span className={styles.trustNumber}>10×</span>
          <span>increase in publishing output</span>
        </div>
        <div className={styles.trustDivider} />
        <div className={styles.trustStat} data-reveal data-delay="2">
          <span className={styles.trustNumber}>&lt; 2 min</span>
          <span>ingestion to draft delivery</span>
        </div>
        <div className={styles.trustDivider} />
        <div className={styles.trustStat} data-reveal data-delay="3">
          <span className={styles.trustNumber}>100%</span>
          <span>approval-gated publishing</span>
        </div>
        <div className={styles.trustDivider} />
        <div className={styles.trustStat} data-reveal data-delay="4">
          <span className={styles.trustNumber}>Zero</span>
          <span>new tools to onboard</span>
        </div>
      </div>
    </div>
  )
}

// ─── How It Works — step mockup cards ────────────────────────────────────────

function MockupIntegrations() {
  return (
    <div className={styles.stepMockup}>
      <div className={styles.smBar}>
        <div className={styles.smDots}><span /><span /><span /></div>
        <span className={styles.smBarTitle}>Vesper Setup · Integrations</span>
      </div>
      <div className={styles.smBody}>
        <p className={styles.smLabel}>Connected sources</p>

        <div className={styles.smIntRow}>
          <div className={`${styles.smIntIcon} ${styles.smIconSlack}`}>
            <svg viewBox="0 0 122.8 122.8" width="20" height="20" xmlns="http://www.w3.org/2000/svg">
              <path d="M25.8 77.6c0 7.1-5.8 12.9-12.9 12.9S0 84.7 0 77.6s5.8-12.9 12.9-12.9h12.9v12.9z" fill="#E01E5A"/>
              <path d="M32.3 77.6c0-7.1 5.8-12.9 12.9-12.9s12.9 5.8 12.9 12.9v32.3c0 7.1-5.8 12.9-12.9 12.9s-12.9-5.8-12.9-12.9V77.6z" fill="#E01E5A"/>
              <path d="M45.2 25.8c-7.1 0-12.9-5.8-12.9-12.9S38.1 0 45.2 0s12.9 5.8 12.9 12.9v12.9H45.2z" fill="#36C5F0"/>
              <path d="M45.2 32.3c7.1 0 12.9 5.8 12.9 12.9s-5.8 12.9-12.9 12.9H12.9C5.8 58.1 0 52.3 0 45.2s5.8-12.9 12.9-12.9h32.3z" fill="#36C5F0"/>
              <path d="M97 45.2c0-7.1 5.8-12.9 12.9-12.9s12.9 5.8 12.9 12.9-5.8 12.9-12.9 12.9H97V45.2z" fill="#2EB67D"/>
              <path d="M90.5 45.2c0 7.1-5.8 12.9-12.9 12.9s-12.9-5.8-12.9-12.9V12.9C64.7 5.8 70.5 0 77.6 0s12.9 5.8 12.9 12.9v32.3z" fill="#2EB67D"/>
              <path d="M77.6 97c7.1 0 12.9 5.8 12.9 12.9s-5.8 12.9-12.9 12.9-12.9-5.8-12.9-12.9V97h12.9z" fill="#ECB22E"/>
              <path d="M77.6 90.5c-7.1 0-12.9-5.8-12.9-12.9s5.8-12.9 12.9-12.9h32.3c7.1 0 12.9 5.8 12.9 12.9s-5.8 12.9-12.9 12.9H77.6z" fill="#ECB22E"/>
            </svg>
          </div>
          <div className={styles.smIntInfo}>
            <strong>Slack</strong>
            <span>3 channels monitored</span>
            <span className={styles.smIntChannels}># wins-and-shoutouts · # general · # product-updates</span>
          </div>
          <span className={styles.smCheck}>✓</span>
        </div>

        <div className={styles.smSep} />

        <div className={styles.smIntRow}>
          <div className={`${styles.smIntIcon} ${styles.smIconGmail}`}>
            <svg viewBox="0 0 24 24" width="20" height="20" xmlns="http://www.w3.org/2000/svg">
              <path d="M24 5.457v13.909c0 .904-.732 1.636-1.636 1.636h-3.819V11.73L12 16.64l-6.545-4.91v9.273H1.636A1.636 1.636 0 0 1 0 19.366V5.457c0-2.023 2.309-3.178 3.927-1.964L5.455 4.64 12 9.548l6.545-4.91 1.528-1.145C21.69 2.28 24 3.434 24 5.457z" fill="#EA4335"/>
            </svg>
          </div>
          <div className={styles.smIntInfo}>
            <strong>Gmail</strong>
            <span>Watching: Starred, Important</span>
          </div>
          <span className={styles.smCheck}>✓</span>
        </div>

        <div className={styles.smFooter}>
          <span className={styles.smPulseDot} />
          Monitoring active · synced 2 min ago
        </div>
      </div>
    </div>
  )
}

function MockupClassify() {
  return (
    <div className={styles.stepMockup}>
      <div className={styles.smBar}>
        <div className={styles.smDots}><span /><span /><span /></div>
        <span className={styles.smBarTitle}>Signal Processing</span>
        <span className={styles.smBadgePurple}>customer_win</span>
      </div>
      <div className={styles.smBody}>
        <blockquote className={styles.smQuote}>
          "Just wrapped a call with TechFlow — 3 months in and their onboarding time dropped 60%! 🚀"
        </blockquote>

        <p className={styles.smLabel}>Classification scores</p>

        <div className={styles.smScoreRow}>
          <span className={styles.smScoreKey}>Signal type</span>
          <span className={styles.smScoreVal}>customer_praise</span>
          <div className={styles.smBar2}><div className={styles.smBarFill} style={{ width: '94%' }} /></div>
          <span className={styles.smScorePct}>94%</span>
        </div>
        <div className={styles.smScoreRow}>
          <span className={styles.smScoreKey}>Content value</span>
          <span className={styles.smScoreVal}>High</span>
          <div className={styles.smBar2}><div className={styles.smBarFill} style={{ width: '88%' }} /></div>
          <span className={styles.smScorePct}>88%</span>
        </div>
        <div className={`${styles.smScoreRow} ${styles.smScoreRowSummary}`}>
          <span className={styles.smScoreKey}>context_summary</span>
          <span className={`${styles.smScoreVal} ${styles.smScoreValSummary}`}>TechFlow praised Vesper after 3 months, reporting a 60% reduction in onboarding time. New employees are fully productive in week one. They reached out unprompted — no check-in scheduled.</span>
        </div>

        <div className={styles.smFooter}>
          <span className={styles.smSpinner} />
          Drafting 3 variants…
        </div>
      </div>
    </div>
  )
}

function MockupApproval() {
  return (
    <div className={styles.stepMockup}>
      <div className={styles.smSlackBar}>
        <div className={styles.smDots}><span /><span /><span /></div>
        <span className={styles.smSlackChannel}># social-queue</span>
        <span className={styles.smSlackMembers}>8 members</span>
      </div>
      <div className={styles.smBody}>
        <div className={styles.smBotMsg}>
          <div className={styles.smBotAvatar}>V</div>
          <div className={styles.smBotRight}>
            <div className={styles.smBotMeta}>
              <strong>Vesper</strong>
              <span className={styles.smBotTag}>App</span>
              <span>just now</span>
            </div>
            <p className={styles.smBotText}>📝 <strong>New draft ready for review</strong></p>
            <div className={styles.smDraftCard}>
              <p className={styles.smDraftText}>
                "We got a message from a customer we hadn't spoken to in 3 months. TechFlow reached out unprompted to say their new hires are fully productive in week one…"
              </p>
              <p className={styles.smDraftMeta}>LinkedIn · customer_praise · 247 words</p>
            </div>
            <div className={styles.smActionsRow}>
              <button className={styles.smBtnApprove}>✓ Approve</button>
              <button className={styles.smBtnSchedule}>Schedule</button>
              <button className={styles.smBtnRewrite}>Rewrite</button>
              <button className={styles.smBtnReject}>Reject</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

const STEP_MOCKUPS: Array<() => React.ReactElement> = [MockupIntegrations, MockupClassify, MockupApproval]

// ─── How It Works ─────────────────────────────────────────────────────────────
function HowItWorksSection() {
  const steps = [
    {
      number: '01',
      heading: 'Integrate your communication stack',
      desc: 'Connect Slack workspaces and Gmail in minutes. Vesper indexes your selected channels and monitors them continuously — no prompts to maintain, no disruption to how your team already works.',
    },
    {
      number: '02',
      heading: 'Intelligent signal classification',
      desc: 'Vesper runs a classification pass on every ingested message — classifying messages across different content signal categories including customer wins, product milestones, hiring announcements, and founder insights. Noise is filtered before it ever reaches your content queue.',
    },
    {
      number: '03',
      heading: 'Approval-gated publishing workflow',
      desc: 'Drafted content surfaces in your dedicated #social-queue channel as structured Slack approval cards. Your team reviews, edits, requests variants, or schedules a post — all without leaving Slack. Nothing publishes without explicit human sign-off.',
    },
  ]

  return (
    <section id="how-it-works" className={styles.howItWorks}>
      <div className={styles.sectionInner}>
        <p className={styles.sectionEyebrow} data-reveal>How it works</p>
        <h2 className={styles.sectionTitle} data-reveal data-delay="1">
          A systematic pipeline from{' '}
          <em className={styles.gradientText}>internal signal</em>{' '}
          to published Linkedin posts
        </h2>
        <p className={styles.sectionSub} data-reveal data-delay="2">
          Vesper replaces ad-hoc content creation with a repeatable, AI-monitored workflow —
          built directly into the tools your team already uses every day.
        </p>
      </div>

      <div className={styles.steps}>
        {steps.map((step, i) => {
          const Mockup = STEP_MOCKUPS[i]
          return (
            <div key={i} className={`${styles.step} ${i % 2 === 1 ? styles.stepReverse : ''}`} data-reveal>
              <div className={styles.stepContent}>
                <span className={styles.stepNumber}>{step.number}</span>
                <h3 className={styles.stepHeading}>{step.heading}</h3>
                <p className={styles.stepDesc}>{step.desc}</p>
              </div>
              <div className={styles.stepMockupWrap}>
                {Mockup && <Mockup />}
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}

// ─── Features ─────────────────────────────────────────────────────────────────
function FeaturesSection() {
  const features = [
    {
      Icon: IconBroadcast,
      heading: 'Continuous channel monitoring',
      desc: 'Persistent background process across Slack channels and Gmail labels — ingesting messages, classifying by signal type, and routing content-worthy moments into your draft queue. No manual triggering.',
    },
    {
      Icon: IconFilter,
      heading: 'Five-category classification',
      desc: 'Every message is scored across customer praise, product wins, launch updates, hiring news, and founder insights — with operational noise filtered before it reaches your queue.',
    },
    {
      Icon: IconShield,
      heading: 'Pre-draft content redaction',
      desc: 'A dedicated redaction pass strips PII, client names, and confidential figures from each signal before generation — ensuring clean, shareable drafts from the first review.',
    },
    {
      Icon: IconDocument,
      heading: 'Multi-variant draft generation',
      desc: 'Each signal produces 2–3 structurally distinct LinkedIn post variants with different hooks, angles, and formats. Pick, edit, or request a new variant — all within Slack.',
    },
    {
      Icon: IconCalendar,
      heading: 'Content calendar & scheduling',
      desc: 'Approve posts into a publishing calendar. Schedule for a specific datetime, choose "next 9am workday," or set recurring windows — with automatic retry on failed publishes.',
    },
    {
      Icon: IconRefresh,
      heading: 'Inline rewrite from Slack',
      desc: 'Reject a draft with a short note and Vesper regenerates immediately with your feedback applied. No prompts to write, no context to re-establish — the loop stays inside Slack.',
    },
  ]

  return (
    <section id="features" className={styles.featuresSection}>
      <div className={styles.sectionInner}>
        <p className={styles.sectionEyebrow} data-reveal>Platform capabilities</p>
        <h2 className={styles.sectionTitle} data-reveal data-delay="1">
          Built for scale. Designed for control.
        </h2>
        <p className={styles.sectionSub} data-reveal data-delay="2">
          Vesper helps growing teams publish consistently, build a real audience, and attract
          potential clients — no content agency, no extra headcount required.
        </p>

        <div className={styles.featuresGrid}>
          {features.map((f, i) => (
            <div
              key={i}
              className={styles.featureCard}
              data-reveal
              data-delay={String((i % 3) + 1)}
            >
              <span className={styles.featureIcon}><f.Icon /></span>
              <h3 className={styles.featureHeading}>{f.heading}</h3>
              <p className={styles.featureDesc}>{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// ─── Pipeline ─────────────────────────────────────────────────────────────────
function PipelineSection() {
  const stages = [
    { icon: '💬', label: 'Signal ingested', sub: 'Slack or Gmail message captured' },
    { icon: '🔍', label: 'Classification', sub: 'Discover and classify content signal' },
    { icon: '🧠', label: 'Story context analysis', sub: 'AI agent that understand the context, tone, and audience fit' },
    { icon: '✨', label: 'Draft generation', sub: '2–3 on-brand variants written' },
    { icon: '✅', label: 'Approval gate', sub: 'Review and adjust in Slack' },
    { icon: '📣', label: 'Published', sub: 'Scheduled and posted to LinkedIn automatically' },
  ]

  return (
    <section className={styles.pipeline}>
      <div className={styles.pipelineInner}>
        <img
          src="https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=1600&q=80&auto=format&fit=crop"
          alt="Team collaboration in a modern workspace"
          className={styles.pipelineBg}
          loading="lazy"
        />
        <div className={styles.pipelineOverlay} />
        <div className={styles.pipelineContent}>
          <p className={styles.pipelineEyebrow}>The pipeline</p>
          <h2 className={styles.pipelineTitle}>
            A structured pipeline from<br />
            <em className={styles.pipelineTitleAccent}>raw signal to published content</em>
          </h2>
          <p className={styles.pipelineSub}>
            Every message travels the same six-stage workflow — ingestion, classification,
            story analysis, draft generation, approval, and publishing — with human sign-off required before anything goes live.
          </p>

          <div className={styles.pipelineStages}>
            {stages.map((stage, i) => (
              <div key={i} className={styles.pipelineStage}>
                <div className={styles.pipelineIcon}>{stage.icon}</div>
                <div className={styles.pipelineStageMeta}>
                  <strong>{stage.label}</strong>
                  <span>{stage.sub}</span>
                </div>
                {i < stages.length - 1 && (
                  <span className={styles.pipelineArrow}>→</span>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}


// ─── Landing (main export) ───────────────────────────────────────────────────
export default function Landing() {
  useScrollReveal()

  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState('')
  const waitlistRef = useRef<HTMLElement>(null)

  const scrollToWaitlist = useCallback(() => {
    waitlistRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setStatus('loading')
    setErrorMessage('')
    try {
      const response = await fetch('/api/waitlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      if (!response.ok) {
        const contentType = response.headers.get('content-type') ?? ''
        let message = 'Failed to join waitlist'
        if (contentType.includes('application/json')) {
          const data = await response.json() as { error?: string }
          message = data.error ?? message
        }
        throw new Error(message)
      }
      setStatus('success')
      setEmail('')
      setTimeout(() => setStatus('idle'), 5000)
    } catch (error) {
      setStatus('error')
      setErrorMessage(
        error instanceof Error ? error.message : 'Something went wrong. Please try again.'
      )
    }
  }

  return (
    <div className={styles.landing}>
      <Navbar onCTA={scrollToWaitlist} />
      <HeroSection onCTA={scrollToWaitlist} />
      <ProblemSection />
      <TrustStrip />
      <HowItWorksSection />
      <FeaturesSection />
      <PipelineSection />

      {/* Waitlist */}
      <section ref={waitlistRef as React.RefObject<HTMLElement>} id="waitlist" className={styles.waitlistSection}>
        <div className={styles.waitlistInner}>
          <p className={styles.sectionEyebrow} data-reveal>Request early access</p>
          <h2 className={styles.waitlistTitle} data-reveal data-delay="1">
            Your internal signals are your{' '}
            <em className={styles.gradientText}>competitive advantage.</em>
          </h2>
          <p className={styles.waitlistSub} data-reveal data-delay="2">
            Most companies are sitting on months of publishable content — buried in Slack
            threads and email chains. Vesper gives your team the infrastructure to surface,
            draft, and publish it systematically. Join the early access list and be first to ship.
          </p>

          <form onSubmit={handleSubmit}>
            <div className={styles.inputGroup}>
              <input
                type="email"
                placeholder="your@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={status === 'loading'}
                className={styles.input}
                aria-label="Work email address"
              />
              <button type="submit" disabled={status === 'loading'} className={styles.button}>
                {status === 'loading' ? 'Joining...' : 'Join Waitlist'}
              </button>
            </div>
            {status === 'success' && (
              <p className={styles.successMessage}>✓ You're on the list — we'll be in touch soon!</p>
            )}
            {status === 'error' && (
              <p className={styles.errorMessage}>✗ Failed! Please try again{errorMessage}</p>
            )}
          </form>
        </div>
      </section>

      {/* Footer */}
      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <div className={styles.footerLogo}>
            <img src="/logo.svg" alt="Vesper" height="40" />
          </div>
          <p className={styles.footerCopy}>© {new Date().getFullYear()} Vesper. All rights reserved.</p>
          <div className={styles.footerLinks}>
            <a href="mailto:andrewt.tu@mail.utoronto.ca">Contact Us</a>
            <a href="/privacy">Privacy Policy</a>
            <a href="/terms">Terms of Service</a>
          </div>
        </div>
      </footer>
    </div>
  )
}
