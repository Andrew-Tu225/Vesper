import styles from '../../pages/landing.module.css'
import {
  LinkedInPostMockup,
  SlackApprovalMockup,
  SlackChannelMockup,
} from './FeatureMockups'

function LinkedInTile({ backdrop = false }: { backdrop?: boolean }) {
  return (
    <div className={`${styles.bentoTile} ${styles.bentoLinkedIn} ${backdrop ? styles.bentoTileBackdrop : ''}`}>
      <div className={styles.bentoTileInner}>
        {!backdrop && <div>
          <h3 className={styles.bentoTileHeading}>LinkedIn-ready post previews</h3>
          <p className={styles.bentoTileDesc}>
            Drafts render in a post-shaped preview so your team can judge pacing, emphasis,
            and visual polish before anything goes live.
          </p>
        </div>}
        <LinkedInPostMockup tone={backdrop ? 'hero' : 'tile'} />
      </div>
    </div>
  )
}

function SlackTile({ backdrop = false }: { backdrop?: boolean }) {
  return (
    <div className={`${styles.bentoTile} ${styles.bentoSlack} ${backdrop ? styles.bentoTileBackdrop : ''}`}>
      <div className={styles.bentoTileInner}>
        {!backdrop && <div>
          <h3 className={styles.bentoTileHeading}>Slack-native signal capture</h3>
          <p className={styles.bentoTileDesc}>
            Monitor the channels your team already uses and surface high-signal stories the
            moment they show up in conversation.
          </p>
        </div>}
        <SlackChannelMockup tone={backdrop ? 'hero' : 'tile'} />
      </div>
    </div>
  )
}

function ApprovalTile({ backdrop = false }: { backdrop?: boolean }) {
  return (
    <div className={`${styles.bentoTile} ${styles.bentoApproval} ${backdrop ? styles.bentoTileBackdrop : ''}`}>
      <div className={styles.bentoTileInner}>
        {!backdrop && <div>
          <h3 className={styles.bentoTileHeading}>Approval stays inside Slack</h3>
          <p className={styles.bentoTileDesc}>
            Review, approve, schedule, or rewrite from a structured Slack card without
            hopping into another tool.
          </p>
        </div>}
        <SlackApprovalMockup tone={backdrop ? 'hero' : 'tile'} />
      </div>
    </div>
  )
}

export function FeaturesBento({ mode = 'section' }: { mode?: 'section' | 'backdrop' }) {
  if (mode === 'backdrop') {
    return (
      <div className={styles.bentoBackdrop} aria-hidden="true">
        <div className={styles.bentoBackdropLinkedIn}><LinkedInTile backdrop /></div>
        <div className={styles.bentoBackdropSlack}><SlackTile backdrop /></div>
        <div className={styles.bentoBackdropApproval}><ApprovalTile backdrop /></div>
      </div>
    )
  }

  return (
    <section id="features" className={styles.bentoSection}>
      <div className={styles.sectionInner}>
        <p className={styles.sectionEyebrow} data-reveal>Platform capabilities</p>
        <h2 className={styles.sectionTitle} data-reveal data-delay="1">
          Built for scale. Designed for control.
        </h2>
        <p className={styles.sectionSub} data-reveal data-delay="2">
          Vesper helps growing teams publish consistently, build a real audience, and attract
          potential clients — no content agency, no extra headcount required.
        </p>
      </div>

      <div className={styles.bentoGrid} data-reveal data-delay="1">
        <LinkedInTile />
        <SlackTile />
        <ApprovalTile />
      </div>
    </section>
  )
}
