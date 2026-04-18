import { Link } from 'react-router-dom'
import styles from './legal.module.css'

export default function PrivacyPolicy() {
  return (
    <div className={styles.page}>
      {/* ── Nav ── */}
      <nav className={styles.nav}>
        <div className={styles.navInner}>
          <Link to="/" className={styles.navLogo}>
            <img src="/logo.svg" alt="Vesper" height="44" />
          </Link>
          <Link to="/" className={styles.navBack}>← Back to home</Link>
        </div>
      </nav>

      {/* ── Content ── */}
      <main className={styles.main}>
        <div className={styles.content}>
          <div className={styles.header}>
            <p className={styles.eyebrow}>Legal</p>
            <h1 className={styles.title}>Privacy Policy</h1>
            <p className={styles.meta}>Last updated: April 17, 2026 · Effective: April 17, 2026</p>
          </div>

          <div className={styles.body}>
            <p className={styles.intro}>
              Vesper ("we," "us," or "our") is committed to protecting the privacy of our
              customers and the teams that use our platform. This Privacy Policy explains what
              information we collect, how we use it, with whom we share it, and the rights
              you have over your data. It applies to all services offered through vesper.ai
              and any associated applications or APIs.
            </p>

            <section className={styles.section}>
              <h2>1. Who We Are</h2>
              <p>
                Vesper is a B2B SaaS product that monitors connected Slack workspaces and Gmail
                accounts, classifies messages as potential thought-leadership content, generates
                draft LinkedIn posts, and routes them through an approval workflow entirely within
                Slack. Our customers are businesses ("Workspace Operators") and their employees
                ("Users") who interact with the platform.
              </p>
            </section>

            <section className={styles.section}>
              <h2>2. Information We Collect</h2>

              <h3>2.1 Information You Provide Directly</h3>
              <p>
                When you sign up for early access or create an account, we collect your name,
                work email address, company name, and any other information you voluntarily
                submit. If you contact our support team, we retain the contents of that
                communication.
              </p>

              <h3>2.2 Workspace and Communication Data</h3>
              <p>
                To provide the core service, Vesper reads messages from Slack channels and Gmail
                labels that Workspace Operators explicitly configure and authorize. We ingest this
                content to classify, redact, and generate LinkedIn draft posts. Specifically:
              </p>
              <ul>
                <li>Slack message content, author metadata, channel names, and timestamps from channels you select</li>
                <li>Gmail message content, subject lines, sender and recipient metadata from labels you authorize</li>
                <li>Reactions, threads, and attachments within monitored channels, where relevant to classification</li>
              </ul>
              <p>
                We do <strong>not</strong> read private direct messages, channels not explicitly
                authorized, or any communication data outside the configured scope.
              </p>

              <h3>2.3 OAuth Tokens and Credentials</h3>
              <p>
                We store the OAuth access tokens required to connect to Slack and Gmail on your
                behalf. All tokens are encrypted at rest using AES-256 and transmitted exclusively
                over TLS 1.2 or higher. We request only the minimum permission scopes necessary
                to perform the service.
              </p>

              <h3>2.4 Usage and Log Data</h3>
              <p>
                We collect operational logs including API request metadata, timestamps, error
                events, and feature interactions. This data does not include the content of
                messages but helps us diagnose issues, monitor performance, and improve the
                service.
              </p>

              <h3>2.5 Waitlist Data</h3>
              <p>
                If you join our waitlist, we collect your email address and store it in our
                contact management system (currently Resend). This is used only to notify you
                when access becomes available and for occasional product updates. You may
                unsubscribe at any time.
              </p>
            </section>

            <section className={styles.section}>
              <h2>3. How We Use Your Information</h2>
              <p>We use the information we collect to:</p>
              <ul>
                <li>Provide, operate, and maintain the Vesper platform</li>
                <li>Classify incoming Slack and Gmail messages against our content signal taxonomy</li>
                <li>Redact personally identifiable information and confidential data from signals before draft generation</li>
                <li>Generate LinkedIn post drafts and route them for human approval within Slack</li>
                <li>Authenticate your identity and maintain account security</li>
                <li>Respond to support requests and troubleshoot issues</li>
                <li>Send service-related communications (e.g., account alerts, approval notifications)</li>
                <li>Improve our classification models and product features using aggregated, anonymised data</li>
                <li>Comply with applicable legal obligations</li>
              </ul>
              <p>
                We do not use your communication content to train third-party AI models, and we
                do not sell your data to advertisers or data brokers.
              </p>
            </section>

            <section className={styles.section}>
              <h2>4. Automated Processing and AI</h2>
              <p>
                Vesper uses OpenAI's API to classify messages and generate post drafts. Message
                content that passes our relevance threshold is transmitted to OpenAI for
                processing. OpenAI does not use API-submitted content to train its models under
                our enterprise agreement. Before any content is sent to OpenAI, our redaction
                pipeline strips identified PII, client names, and sensitive figures.
              </p>
              <p>
                All AI-generated drafts require explicit human approval before any content is
                published to LinkedIn. No content is ever published automatically.
              </p>
            </section>

            <section className={styles.section}>
              <h2>5. Data Sharing and Disclosure</h2>
              <p>
                We do not sell or rent your personal information. We share information only in
                the following circumstances:
              </p>
              <ul>
                <li>
                  <strong>Service providers:</strong> We engage sub-processors including OpenAI
                  (AI generation), Resend (email and contact management), and cloud infrastructure
                  providers (hosting and databases). Each is bound by confidentiality obligations
                  and data processing agreements.
                </li>
                <li>
                  <strong>Workspace Operators:</strong> Usage statistics and activity logs may be
                  visible to authorized administrators within your organization.
                </li>
                <li>
                  <strong>Legal compliance:</strong> We may disclose information if required by
                  law, regulation, court order, or governmental authority, or where necessary to
                  protect the rights, property, or safety of Vesper, its users, or the public.
                </li>
                <li>
                  <strong>Business transfers:</strong> In the event of a merger, acquisition, or
                  sale of assets, your data may be transferred to the successor entity, subject
                  to the same privacy protections described here.
                </li>
              </ul>
            </section>

            <section className={styles.section}>
              <h2>6. Data Retention</h2>
              <p>
                We retain account data for as long as your subscription is active plus 90 days
                following termination, unless a longer retention period is required by law or
                you request deletion earlier. Ingested message content used for classification
                and draft generation is retained for 12 months to support audit trails and
                re-generation requests. Anonymised, aggregated analytics may be retained
                indefinitely.
              </p>
              <p>
                When a workspace is disconnected, we cease ingesting new messages from that
                source within 24 hours. Deletion requests for historical data are processed
                within 30 days.
              </p>
            </section>

            <section className={styles.section}>
              <h2>7. Security</h2>
              <p>
                We implement industry-standard security controls including:
              </p>
              <ul>
                <li>AES-256 encryption for all OAuth tokens and sensitive data at rest</li>
                <li>TLS 1.2+ for all data in transit</li>
                <li>Role-based access controls limiting internal employee access to customer data</li>
                <li>Regular security reviews and dependency audits</li>
                <li>Isolated worker processes for message ingestion to minimize data exposure</li>
              </ul>
              <p>
                No security system is impenetrable. In the event of a data breach that affects
                your personal information, we will notify you in accordance with applicable law.
              </p>
            </section>

            <section className={styles.section}>
              <h2>8. Your Rights</h2>
              <p>
                Depending on your location, you may have the following rights regarding your
                personal data:
              </p>
              <ul>
                <li><strong>Access:</strong> Request a copy of the personal data we hold about you.</li>
                <li><strong>Correction:</strong> Request correction of inaccurate or incomplete data.</li>
                <li><strong>Deletion:</strong> Request that we delete your personal data, subject to certain legal exceptions.</li>
                <li><strong>Portability:</strong> Request your data in a structured, machine-readable format.</li>
                <li><strong>Objection:</strong> Object to processing based on legitimate interests.</li>
                <li><strong>Restriction:</strong> Request that we restrict processing of your data in certain circumstances.</li>
                <li><strong>Withdraw consent:</strong> Where processing is based on your consent, you may withdraw it at any time.</li>
              </ul>
              <p>
                To exercise any of these rights,{' '}
                <a href="mailto:andrewt.tu@mail.utoronto.ca">contact us</a>. We will respond within
                30 days. We may ask you to verify your identity before processing your request.
              </p>
            </section>

            <section className={styles.section}>
              <h2>9. International Transfers</h2>
              <p>
                Vesper is operated from Canada. If you are located in the European Economic Area,
                United Kingdom, or other jurisdictions with data transfer restrictions, your
                information may be transferred to and processed in countries that do not have the
                same data protection laws as your jurisdiction. Where required, we rely on
                Standard Contractual Clauses or other approved transfer mechanisms.
              </p>
            </section>

            <section className={styles.section}>
              <h2>10. Children's Privacy</h2>
              <p>
                Vesper is a business-to-business service not directed at individuals under the
                age of 16. We do not knowingly collect personal information from minors. If we
                become aware that we have collected data from a minor, we will delete it promptly.
              </p>
            </section>

            <section className={styles.section}>
              <h2>11. Third-Party Links</h2>
              <p>
                Our platform may contain links to external services (e.g., LinkedIn, Slack,
                Google). This Privacy Policy does not apply to those third-party services. We
                encourage you to review their privacy policies separately.
              </p>
            </section>

            <section className={styles.section}>
              <h2>12. Changes to This Policy</h2>
              <p>
                We may update this Privacy Policy from time to time. When we make material
                changes, we will notify you by email or by displaying a prominent notice within
                the platform. The updated policy will be effective upon posting. Continued use
                of the service after changes take effect constitutes your acceptance of the
                revised policy.
              </p>
            </section>

            <section className={styles.section}>
              <h2>13. Contact Us</h2>
              <p>
                If you have questions, concerns, or requests regarding this Privacy Policy or our
                data practices, please reach out to us:
              </p>
              <div className={styles.contactBlock}>
                <p><strong>Vesper</strong></p>
                <p><a href="mailto:andrewt.tu@mail.utoronto.ca">Contact us</a></p>
              </div>
            </section>
          </div>
        </div>
      </main>

      {/* ── Footer ── */}
      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <p className={styles.footerCopy}>© {new Date().getFullYear()} Vesper. All rights reserved.</p>
          <div className={styles.footerLinks}>
            <Link to="/privacy" className={styles.footerLink}>Privacy Policy</Link>
            <Link to="/terms" className={styles.footerLink}>Terms of Service</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
