import { useSearchParams } from 'react-router-dom'
import { getParam } from '@/lib/api'
import { SurfaceCard } from '@/components/ui/SurfaceCard'
import '@/components/ui/ui.css'

type OnboardingStep = 'connect_slack' | 'connect_linkedin' | 'seed_style_library'

const STEPS: Record<OnboardingStep, { title: string; description: string; action?: { label: string; href: string } }> = {
  connect_slack: {
    title: 'Connect Slack',
    description: 'Allow Vesper to read selected channels and post approval cards to your team.',
    action: { label: 'Connect Slack', href: '/api/oauth/slack/install' },
  },
  connect_linkedin: {
    title: 'Connect LinkedIn',
    description: 'Grant Vesper permission to publish posts to your LinkedIn company page.',
    action: { label: 'Connect LinkedIn', href: '/api/oauth/linkedin/install' },
  },
  seed_style_library: {
    title: 'Seed Your Style Library',
    description:
      'Add at least 5 approved LinkedIn posts to teach Vesper your brand voice. You can do this from the Style Library page.',
    action: { label: 'Go to Style Library', href: '/style-library' },
  },
}

const STEP_ORDER: OnboardingStep[] = ['connect_slack', 'connect_linkedin', 'seed_style_library']

function isValidStep(step: string): step is OnboardingStep {
  return STEP_ORDER.includes(step as OnboardingStep)
}

export default function Onboarding() {
  const [params] = useSearchParams()
  const rawStep = getParam(params, 'step', 'connect_slack')
  const error = params.get('error')
  const currentStep: OnboardingStep = isValidStep(rawStep) ? rawStep : 'connect_slack'
  const stepInfo = STEPS[currentStep]

  return (
    <div>
      <h1 style={{ marginBottom: 'var(--space-2)' }}>Get started</h1>
      <p style={{ color: 'var(--color-text-muted)', marginBottom: 'var(--space-8)' }}>
        Complete the steps below to set up Vesper for your workspace.
      </p>

      {/* Step progress */}
      <div style={{ display: 'flex', gap: 'var(--space-2)', marginBottom: 'var(--space-8)' }}>
        {STEP_ORDER.map((step, idx) => {
          const isDone = STEP_ORDER.indexOf(currentStep) > idx
          const isActive = step === currentStep
          return (
            <div
              key={step}
              style={{
                flex: 1,
                height: '4px',
                borderRadius: '2px',
                background: isDone
                  ? 'var(--color-success)'
                  : isActive
                    ? 'var(--color-accent)'
                    : 'var(--color-border)',
                transition: 'background var(--duration-base) var(--ease-out)',
              }}
            />
          )
        })}
      </div>

      {error && (
        <div className="error-banner" style={{ marginBottom: 'var(--space-6)' }}>
          {error === 'access_denied'
            ? 'Access was denied. Please try again.'
            : `Something went wrong: ${error}`}
        </div>
      )}

      <SurfaceCard>
        <h2 style={{ marginBottom: 'var(--space-3)' }}>{stepInfo.title}</h2>
        <p style={{ color: 'var(--color-text-muted)', marginBottom: 'var(--space-6)' }}>
          {stepInfo.description}
        </p>
        {stepInfo.action && (
          <a href={stepInfo.action.href} className="btn btn--primary">
            {stepInfo.action.label}
          </a>
        )}
      </SurfaceCard>
    </div>
  )
}
