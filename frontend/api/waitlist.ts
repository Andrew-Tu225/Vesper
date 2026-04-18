import { Resend } from 'resend'

export const config = {
  runtime: 'edge'
}

export default async function handler(req: Request): Promise<Response> {
  const apiKey = process.env.RESEND_API_KEY
  const audienceId = process.env.RESEND_AUDIENCE_ID

  // Validate env vars
  if (!apiKey || !audienceId) {
    return new Response(
      JSON.stringify({ error: 'Server configuration error: missing Resend credentials' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }

  const resend = new Resend(apiKey)

  // Only accept POST
  if (req.method !== 'POST') {
    return new Response(JSON.stringify({ error: 'Method not allowed' }), {
      status: 405,
      headers: { 'Content-Type': 'application/json' }
    })
  }

  try {
    const { email } = (await req.json()) as { email?: string }

    // Validate email
    if (!email || typeof email !== 'string' || !isValidEmail(email)) {
      return new Response(JSON.stringify({ error: 'Invalid email address' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      })
    }

    // Add to Resend audience
    const response = await resend.contacts.create({
      email,
      audienceId
    })

    if (response.error) {
      throw new Error(response.error.message)
    }

    return new Response(JSON.stringify({ success: true, data: response.data }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    })
  } catch (error) {
    const message =
      error instanceof Error ? error.message : 'Failed to process request'

    return new Response(JSON.stringify({ error: message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    })
  }
}

function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}


