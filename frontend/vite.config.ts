import { defineConfig } from 'vitest/config'
import { loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import type { IncomingMessage, ServerResponse } from 'node:http'

export default defineConfig(({ mode }) => {
  // loadEnv with prefix '' loads ALL .env vars (not just VITE_-prefixed ones)
  // so RESEND_API_KEY and RESEND_AUDIENCE_ID are available server-side
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [
      react(),
      {
        // Handle Vercel edge-function routes locally so they don't hit the
        // FastAPI proxy and cause ECONNREFUSED errors in development.
        name: 'vercel-edge-dev',
        configureServer(server) {
          server.middlewares.use(
            '/api/waitlist',
            async (req: IncomingMessage, res: ServerResponse) => {
              res.setHeader('Content-Type', 'application/json')

              if (req.method !== 'POST') {
                res.statusCode = 405
                res.end(JSON.stringify({ error: 'Method not allowed' }))
                return
              }

              const apiKey = env.RESEND_API_KEY
              const audienceId = env.RESEND_AUDIENCE_ID

              const chunks: Buffer[] = []
              req.on('data', (c: Buffer) => chunks.push(c))
              req.on('end', async () => {
                let email: string | undefined
                try {
                  const body = JSON.parse(Buffer.concat(chunks).toString()) as { email?: string }
                  email = body.email
                } catch {
                  res.statusCode = 400
                  res.end(JSON.stringify({ error: 'Invalid JSON' }))
                  return
                }

                // No Resend credentials → dev mock
                if (!apiKey || !audienceId) {
                  console.log('[waitlist dev] mock success (no Resend keys) for:', email)
                  res.statusCode = 200
                  res.end(JSON.stringify({ success: true }))
                  return
                }

                // Resend credentials present → call the real Contacts API
                try {
                  const r = await fetch(
                    `https://api.resend.com/audiences/${audienceId}/contacts`,
                    {
                      method: 'POST',
                      headers: {
                        Authorization: `Bearer ${apiKey}`,
                        'Content-Type': 'application/json',
                      },
                      body: JSON.stringify({ email }),
                    }
                  )
                  const data = await r.json() as unknown
                  if (r.ok) {
                    res.statusCode = 200
                    res.end(JSON.stringify({ success: true, data }))
                  } else {
                    console.error('[waitlist dev] Resend error:', data)
                    res.statusCode = r.status
                    res.end(JSON.stringify({ error: 'Resend error', detail: data }))
                  }
                } catch (e) {
                  res.statusCode = 500
                  res.end(JSON.stringify({ error: String(e) }))
                }
              })
            }
          )
        },
      },
    ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
          // Cookies (vesper_session) flow through automatically when using
          // relative /api/... paths. Never use absolute http://localhost:8000 URLs.
        },
      },
    },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['./src/test/setup.ts'],
    },
  }
})
