import '@/components/ui/ui.css'

export default function Login() {
  return (
    <div
      style={{
        minHeight: '100dvh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--space-8)',
      }}
    >
      <div style={{ maxWidth: '360px', width: '100%', textAlign: 'center' }}>
        <h1
          style={{
            fontFamily: 'var(--font-display)',
            fontSize: 'var(--text-3xl)',
            marginBottom: 'var(--space-2)',
          }}
        >
          Vesper
        </h1>
        <p style={{ color: 'var(--color-text-muted)', marginBottom: 'var(--space-8)' }}>
          Turn internal signals into LinkedIn posts.
        </p>
        <a
          href="/api/auth/google/login"
          className="btn btn--primary"
          style={{ width: '100%', justifyContent: 'center' }}
        >
          Sign in with Google
        </a>
      </div>
    </div>
  )
}
