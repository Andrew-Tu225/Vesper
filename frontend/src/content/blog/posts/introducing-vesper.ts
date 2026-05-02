import type { BlogPost } from '../types'

const post: BlogPost = {
  slug: 'introducing-vesper',
  title: 'Introducing Vesper — the AI Content Assistant Built for B2B Teams',
  subtitle: 'Your team is generating your best content every day. It is just stuck in Slack.',
  category: 'product',
  eyebrow: 'Product · Launch',
  featured: true,
  author: {
    name: 'Andrew Tu',
    role: 'Founder, Vesper',
  },
  publishedAt: '2025-05-02',
  readingMinutes: 6,
  excerpt:
    'Most B2B SaaS teams know they should be posting on LinkedIn. The research is clear. And yet — most teams post sporadically at best, or not at all. Not because they lack things to say, but because no system is watching.',
  seo: {
    title: 'Introducing Vesper — AI Content Assistant for B2B Founders and GTM Teams',
    description:
      'Vesper monitors your Slack workspace, surfaces the moments worth sharing, and drafts LinkedIn posts for your team to approve. Built for B2B SaaS founders and GTM leaders.',
    keywords: [
      'AI content assistant',
      'B2B LinkedIn content',
      'Slack to LinkedIn',
      'content marketing for SaaS',
      'GTM content automation',
      'founder content strategy',
    ],
  },
  body: [
    {
      type: 'paragraph',
      text: 'Most B2B SaaS companies know they should be posting on LinkedIn. The research is clear: consistent thought leadership from founders and teams drives real pipeline. Demos get warmer. Inbound ticks up. Hiring gets easier.',
    },
    {
      type: 'paragraph',
      text: 'And yet — most teams post sporadically at best, or not at all. Not because they lack things to say. The opposite is true.',
    },
    {
      type: 'heading',
      level: 2,
      text: 'The bottleneck is not strategy',
    },
    {
      type: 'paragraph',
      text: 'Walk through any active Slack workspace and you will find it: a customer just sent a message calling your product the tool that saved their Q3. Someone on the product team shipped a feature that took three months to build. The founder shared a hard-won lesson in the founders channel that got twenty reactions.',
    },
    {
      type: 'paragraph',
      text: 'None of it made it to LinkedIn.',
    },
    {
      type: 'paragraph',
      text: 'The raw material for compelling B2B content — customer wins, product moments, founder insights — is being produced constantly inside your organization. The bottleneck is not content strategy. It is that no system is watching.',
    },
    {
      type: 'pullquote',
      text: 'The bottleneck is not content strategy. It is that no system is watching.',
    },
    {
      type: 'heading',
      level: 2,
      text: 'What Vesper does',
    },
    {
      type: 'paragraph',
      text: 'Vesper sits inside Slack — the tool your team already lives in — and monitors the channels you choose. When it detects something worth sharing, it classifies the signal type: a customer compliment, a product milestone, a founder insight, a hiring announcement.',
    },
    {
      type: 'paragraph',
      text: 'Then it drafts two LinkedIn post variants — tailored to your brand voice — and routes them to a dedicated review channel. Your team glances at the card, picks a variant, edits if needed, and schedules it for the time that works best. Vesper publishes at the exact moment you chose. The whole review takes about ten minutes a week.',
    },
    {
      type: 'callout',
      tone: 'insight',
      text: 'Ten minutes a week is all it takes. Vesper surfaces the moments, writes the drafts, and publishes on your schedule — your team just makes the call on what goes out.',
    },
    {
      type: 'paragraph',
      text: 'The AI handles the pattern recognition and the first draft. Your team handles the judgment call. The publishing happens automatically at the time you set. That division of labor is intentional.',
    },
    {
      type: 'heading',
      level: 2,
      text: 'Who this is built for',
    },
    {
      type: 'paragraph',
      text: 'We built Vesper specifically for three types of people we kept meeting:',
    },
    {
      type: 'list',
      style: 'bulleted',
      items: [
        'B2B SaaS founders who know LinkedIn matters for distribution but do not have time to write consistently — or cannot delegate it without losing their voice.',
        'GTM leaders who understand that inbound starts with brand presence, but are fighting to keep up with pipeline and have no bandwidth left for content.',
        'Early-stage marketing teams — often one person or zero — trying to cover social, demand gen, events, and content simultaneously.',
      ],
    },
    {
      type: 'paragraph',
      text: 'The common thread: the team is already producing content-grade raw material every day. Vesper is the system that makes sure it reaches your audience.',
    },
    {
      type: 'heading',
      level: 2,
      text: 'What we deliberately left out',
    },
    {
      type: 'paragraph',
      text: 'We made deliberate decisions about what Vesper is not — and we think these constraints matter.',
    },
    {
      type: 'list',
      style: 'bulleted',
      items: [
        'Scheduled publishing, not manual posting. Your team reviews drafts and schedules them — Vesper handles the actual publishing at the time you set. You get automated consistency without giving up control.',
        'LinkedIn-first. That is where B2B influence actually lives for most teams. We will expand from there, not before.',
        'One brand voice per workspace. Personalization per author is on the roadmap. For now we would rather ship something that works well than something that tries to do everything.',
        'No meeting transcripts. Slack-first and intentional. We will add more sources when the signal-to-noise tradeoff makes sense.',
      ],
    },
    {
      type: 'heading',
      level: 2,
      text: 'Try it',
    },
    {
      type: 'paragraph',
      text: 'If your team is generating wins that never make it to your audience, Vesper is free to try for your first month. Connect your Slack workspace, pick a few channels to monitor, and see what surfaces in your first week.',
    },
    {
      type: 'paragraph',
      text: 'The content is already there. We built the system to find it.',
    },
  ],
}

export default post