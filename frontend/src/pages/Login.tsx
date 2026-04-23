import '@/components/ui/ui.css'
import './login.css'

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4" />
      <path d="M9 18c2.43 0 4.467-.806 5.956-2.18L12.048 13.56C11.242 14.1 10.212 14.42 9 14.42c-2.392 0-4.414-1.616-5.135-3.786H.957v2.332C2.438 15.983 5.482 18 9 18z" fill="#34A853" />
      <path d="M3.865 10.634A5.476 5.476 0 0 1 3.53 9c0-.563.096-1.11.335-1.634V5.034H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.034l2.908-2.4z" fill="#FBBC05" />
      <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0 5.482 0 2.438 2.017.957 4.966L3.865 7.366C4.586 5.196 6.608 3.58 9 3.58z" fill="#EA4335" />
    </svg>
  )
}

export default function Login() {
  return (
    <div className="login-root">
      <div className="login-card">
        <div className="login-logo">
          <img src="/logo.svg" alt="Vesper" height="38" />
        </div>

        <h1 className="login-heading">Sign in to Vesper</h1>
        <p className="login-sub">
          Connect your workspace and start turning internal signals into LinkedIn posts.
        </p>

        <a href="/api/auth/google/login" className="login-google-btn">
          <GoogleIcon />
          Continue with Google
        </a>

        <div className="login-trust">
          <span className="login-trust__pill">
            <span className="login-trust__pill-dot" />
            Free to start
          </span>
          <span className="login-trust__pill">
            <span className="login-trust__pill-dot" />
            No card required
          </span>
          <span className="login-trust__pill">
            <span className="login-trust__pill-dot" />
            100% approval-gated
          </span>
        </div>

        <p className="login-footer">
          By signing in you agree to our{' '}
          <a href="/terms">Terms of Service</a> and{' '}
          <a href="/privacy">Privacy Policy</a>.
        </p>
      </div>
    </div>
  )
}