import { Link } from 'react-router-dom'
import styles from './legal.module.css'

export default function TermsOfService() {
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
            <h1 className={styles.title}>Terms of Service</h1>
            <p className={styles.meta}>Last updated: April 17, 2026 · Effective: April 17, 2026</p>
          </div>

          <div className={styles.body}>
            <p className={styles.intro}>
              These Terms of Service ("Terms") constitute a legally binding agreement between
              Vesper ("Vesper," "we," "us," or "our") and you, either as an individual or on
              behalf of the organization you represent ("Customer," "you," or "your"). By
              accessing or using the Vesper platform, you agree to be bound by these Terms.
              If you do not agree, do not use the service.
            </p>

            <section className={styles.section}>
              <h2>1. The Service</h2>
              <p>
                Vesper provides a B2B SaaS platform that integrates with Slack workspaces and
                Gmail accounts to monitor designated communication channels, classify messages
                as potential thought-leadership content, generate draft LinkedIn posts using AI,
                and route those drafts through a human approval workflow within Slack ("the
                Service"). Access to the Service is provided on a subscription basis.
              </p>
              <p>
                The Service is in active development. Features may change, be added, or be
                removed during your subscription. We will make reasonable efforts to notify
                you of significant changes that materially affect your use of the Service.
              </p>
            </section>

            <section className={styles.section}>
              <h2>2. Eligibility and Account Registration</h2>
              <p>
                You must be at least 18 years of age and have the legal authority to bind
                yourself or your organization to these Terms. By using the Service, you
                represent and warrant that you meet these requirements.
              </p>
              <p>
                You are responsible for maintaining the confidentiality of your account
                credentials and for all activity that occurs under your account. You agree to
                notify us immediately by{' '}
                <a href="mailto:andrewt.tu@mail.utoronto.ca">contacting us</a> if you suspect any
                unauthorized use of your account.
              </p>
            </section>

            <section className={styles.section}>
              <h2>3. Acceptable Use</h2>
              <p>You agree to use the Service only for lawful purposes and in accordance with these Terms. You must not:</p>
              <ul>
                <li>Use the Service to generate or publish content that is false, misleading, defamatory, harassing, or otherwise unlawful</li>
                <li>Connect Slack channels or Gmail accounts for which you do not have authorization from the workspace or account owner</li>
                <li>Attempt to reverse-engineer, decompile, or extract source code from the Service</li>
                <li>Circumvent, disable, or interfere with security features of the Service</li>
                <li>Use the Service to transmit malware, spam, or any harmful code</li>
                <li>Resell, sublicense, or otherwise transfer rights to the Service without our written consent</li>
                <li>Use automated scraping or bulk data extraction tools against the Service's infrastructure</li>
                <li>Publish AI-generated LinkedIn content without human review and approval as contemplated by the Service's approval workflow</li>
              </ul>
            </section>

            <section className={styles.section}>
              <h2>4. Customer Data and Permissions</h2>
              <p>
                You retain ownership of all data you input into or generate through the Service,
                including messages from your Slack channels and Gmail accounts ("Customer Data").
                By connecting these sources, you grant Vesper a limited, non-exclusive,
                revocable licence to access, process, and store Customer Data solely for the
                purpose of providing the Service.
              </p>
              <p>
                You represent and warrant that you have the right and authority to grant this
                licence, including any necessary consents from employees or other individuals
                whose communications may be processed. It is your responsibility to ensure that
                your use of the Service complies with your organization's policies and any
                applicable employment or privacy laws.
              </p>
              <p>
                You acknowledge that Vesper uses third-party AI providers (currently OpenAI) to
                classify and generate content, and that Customer Data may be transmitted to such
                providers subject to the terms of our Privacy Policy.
              </p>
            </section>

            <section className={styles.section}>
              <h2>5. LinkedIn and Third-Party Platform Compliance</h2>
              <p>
                You are solely responsible for ensuring that content published to LinkedIn
                through or facilitated by the Service complies with LinkedIn's User Agreement,
                Professional Community Policies, and any applicable advertising or disclosure
                regulations. Vesper does not review published content for compliance with
                LinkedIn's policies and assumes no liability for content you choose to publish.
              </p>
              <p>
                You acknowledge that third-party integrations (Slack, Gmail, LinkedIn) are
                governed by their respective terms and that Vesper cannot guarantee the
                continued availability of those integrations.
              </p>
            </section>

            <section className={styles.section}>
              <h2>6. Subscription, Billing, and Payment</h2>
              <p>
                During early access and the waitlist period, Vesper may provide access at no
                charge or at promotional pricing. Founding member pricing committed during this
                period will be honoured for the duration of the initial subscription term.
                Paid subscription terms, billing cycles, and pricing will be communicated
                before any charges are applied.
              </p>
              <p>
                Unless otherwise stated, subscriptions automatically renew for successive
                periods equal to the initial subscription term. You may cancel your
                subscription before the renewal date by{' '}
                <a href="mailto:andrewt.tu@mail.utoronto.ca">contacting us</a>. Fees paid are
                non-refundable except where required by applicable law or as otherwise agreed
                in writing.
              </p>
              <p>
                We reserve the right to change subscription fees with 30 days' written notice.
                Your continued use of the Service after the notice period constitutes acceptance
                of the new pricing.
              </p>
            </section>

            <section className={styles.section}>
              <h2>7. Intellectual Property</h2>
              <p>
                The Vesper platform, including its software, visual design, trademarks,
                classification models, and documentation, is the exclusive property of Vesper
                and its licensors. Nothing in these Terms transfers any intellectual property
                rights to you.
              </p>
              <p>
                AI-generated drafts produced by the Service are provided to you as a
                deliverable of the Service. You may use, edit, and publish such drafts in
                accordance with these Terms. Vesper makes no warranty that AI-generated
                content is original, non-infringing, or suitable for publication.
              </p>
              <p>
                If you provide feedback, suggestions, or feature requests, you grant Vesper a
                royalty-free, irrevocable licence to use such feedback for any purpose,
                including improving the Service, without obligation to you.
              </p>
            </section>

            <section className={styles.section}>
              <h2>8. Confidentiality</h2>
              <p>
                Each party agrees to keep confidential any non-public information received from
                the other party in connection with the Service ("Confidential Information"),
                using at least the same degree of care it uses to protect its own confidential
                information. This obligation does not apply to information that is publicly
                available, independently developed, or required to be disclosed by law.
              </p>
            </section>

            <section className={styles.section}>
              <h2>9. Disclaimer of Warranties</h2>
              <p>
                THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTY OF ANY
                KIND. TO THE MAXIMUM EXTENT PERMITTED BY LAW, VESPER DISCLAIMS ALL WARRANTIES,
                EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY,
                FITNESS FOR A PARTICULAR PURPOSE, NON-INFRINGEMENT, AND ACCURACY. WE DO NOT
                WARRANT THAT THE SERVICE WILL BE UNINTERRUPTED, ERROR-FREE, OR FREE OF HARMFUL
                COMPONENTS, OR THAT AI-GENERATED CONTENT WILL BE ACCURATE, COMPLETE, OR
                SUITABLE FOR YOUR INTENDED PURPOSE.
              </p>
            </section>

            <section className={styles.section}>
              <h2>10. Limitation of Liability</h2>
              <p>
                TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, VESPER AND ITS OFFICERS,
                DIRECTORS, EMPLOYEES, AND AGENTS SHALL NOT BE LIABLE FOR ANY INDIRECT,
                INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR DAMAGES FOR LOSS
                OF PROFITS, REVENUE, DATA, GOODWILL, OR BUSINESS INTERRUPTION, ARISING FROM
                YOUR USE OF OR INABILITY TO USE THE SERVICE, EVEN IF VESPER HAS BEEN ADVISED
                OF THE POSSIBILITY OF SUCH DAMAGES.
              </p>
              <p>
                IN NO EVENT SHALL VESPER'S TOTAL CUMULATIVE LIABILITY TO YOU FOR ANY CLAIMS
                ARISING OUT OF OR RELATING TO THESE TERMS EXCEED THE GREATER OF (A) THE FEES
                YOU PAID TO VESPER IN THE 12 MONTHS PRECEDING THE CLAIM OR (B) $100 CAD.
              </p>
              <p>
                Some jurisdictions do not allow the exclusion or limitation of certain warranties
                or liabilities. In such jurisdictions, our liability will be limited to the
                fullest extent permitted by law.
              </p>
            </section>

            <section className={styles.section}>
              <h2>11. Indemnification</h2>
              <p>
                You agree to defend, indemnify, and hold harmless Vesper and its officers,
                directors, employees, and agents from and against any claims, damages, losses,
                liabilities, costs, and expenses (including reasonable legal fees) arising from:
                (a) your use of the Service in violation of these Terms; (b) Customer Data you
                submit or cause to be processed; (c) content you publish to LinkedIn or other
                platforms; or (d) your violation of any third-party rights or applicable law.
              </p>
            </section>

            <section className={styles.section}>
              <h2>12. Term and Termination</h2>
              <p>
                These Terms remain in effect for as long as you use the Service or have an
                active subscription. Either party may terminate the agreement with 30 days'
                written notice. We may suspend or terminate your access immediately if you
                materially breach these Terms, fail to pay fees when due, or if required by law.
              </p>
              <p>
                Upon termination, your right to access and use the Service ceases immediately.
                Sections 4 (Customer Data ownership), 7 (IP), 9 (Disclaimers), 10 (Limitation
                of Liability), 11 (Indemnification), and 13 (Governing Law) survive termination.
              </p>
            </section>

            <section className={styles.section}>
              <h2>13. Governing Law and Dispute Resolution</h2>
              <p>
                These Terms are governed by and construed in accordance with the laws of the
                Province of Ontario and the federal laws of Canada applicable therein, without
                regard to conflict of law principles. You agree to submit to the exclusive
                jurisdiction of the courts of Toronto, Ontario for any disputes arising from
                these Terms or your use of the Service.
              </p>
              <p>
                Before initiating any formal legal proceeding, the parties agree to attempt
                to resolve disputes informally by{' '}
                <a href="mailto:andrewt.tu@mail.utoronto.ca">contacting us</a> and allowing 30 days
                for good-faith negotiation.
              </p>
            </section>

            <section className={styles.section}>
              <h2>14. Changes to These Terms</h2>
              <p>
                We may revise these Terms from time to time. We will provide at least 14 days'
                notice of material changes by email or by posting a notice within the Service.
                Continued use of the Service after the effective date of the revised Terms
                constitutes your acceptance. If you do not agree to the revised Terms, you must
                stop using the Service before the effective date.
              </p>
            </section>

            <section className={styles.section}>
              <h2>15. General Provisions</h2>
              <p>
                <strong>Entire Agreement.</strong> These Terms, together with our Privacy Policy
                and any order forms or subscription agreements, constitute the entire agreement
                between you and Vesper regarding the Service and supersede any prior agreements.
              </p>
              <p>
                <strong>Severability.</strong> If any provision of these Terms is found
                unenforceable, it will be modified to the minimum extent necessary to make it
                enforceable, and the remaining provisions will remain in full force.
              </p>
              <p>
                <strong>Waiver.</strong> Our failure to enforce any right or provision does not
                constitute a waiver of that right or provision.
              </p>
              <p>
                <strong>Assignment.</strong> You may not assign these Terms or any rights under
                them without our written consent. Vesper may assign these Terms in connection
                with a merger, acquisition, or sale of assets.
              </p>
              <p>
                <strong>Force Majeure.</strong> Neither party will be liable for delays or
                failures in performance resulting from causes beyond their reasonable control.
              </p>
            </section>

            <section className={styles.section}>
              <h2>16. Contact</h2>
              <p>
                For questions about these Terms, please contact us at:
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
