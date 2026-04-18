export const config = {
  runtime: 'edge'
}

export default async function handler(req: Request): Promise<Response> {
  const apiKey = process.env.RESEND_API_KEY
  const audienceId = process.env.RESEND_AUDIENCE_ID

  if (!apiKey || !audienceId) {
    return json({ error: 'Server configuration error: missing Resend credentials' }, 500)
  }

  if (req.method !== 'POST') {
    return json({ error: 'Method not allowed' }, 405)
  }

  let email: string | undefined
  try {
    const body = await req.json() as { email?: string }
    email = body.email
  } catch {
    return json({ error: 'Invalid JSON body' }, 400)
  }

  if (!email || !isValidEmail(email)) {
    return json({ error: 'Invalid email address' }, 400)
  }

  const r = await fetch(`https://api.resend.com/audiences/${audienceId}/contacts`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email }),
  })

  const data = await r.json() as unknown
  if (!r.ok) {
    return json({ error: 'Failed to add contact', detail: data }, r.status)
  }

  return json({ success: true, data })
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}
