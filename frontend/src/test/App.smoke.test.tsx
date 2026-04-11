import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi } from 'vitest'
import App from '@/App'

// /api/auth/me always returns 401 in unit tests — user is unauthenticated
globalThis.fetch = vi.fn().mockResolvedValue({
  ok: false,
  status: 401,
  json: async () => ({ detail: 'Not authenticated' }),
})

function renderApp(initialPath = '/') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialPath]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('App smoke tests', () => {
  it('renders the login page at /login', () => {
    renderApp('/login')
    expect(screen.getByText('Vesper')).toBeInTheDocument()
    expect(screen.getByText(/sign in with google/i)).toBeInTheDocument()
  })

  it('redirects unauthenticated users from / to login', async () => {
    renderApp('/')
    // RequireAuth redirects to /login when /api/auth/me returns 401
    expect(await screen.findByText(/sign in with google/i)).toBeInTheDocument()
  })

  it('shows 404 page for unknown routes', () => {
    renderApp('/this-does-not-exist')
    expect(screen.getByText(/404/i)).toBeInTheDocument()
  })
})
