export const ROUTES = {
  LOGIN: '/login',
  AUTH_CALLBACK: '/auth/callback',
  DASHBOARD: '/dashboard',
  QUEUE: '/queue',
  CALENDAR: '/calendar',
  CHANNEL_SETUP: '/channel-setup',
  SETTINGS: '/settings',
  BLOG_INDEX: '/blog',
  BLOG_POST: '/blog/:slug',
} as const

export function blogPostHref(slug: string): string {
  return `/blog/${slug}`
}

export const NAV_ITEMS = [
  { label: 'Dashboard', route: ROUTES.DASHBOARD, icon: 'home' },
  { label: 'Queue', route: ROUTES.QUEUE, icon: 'inbox' },
  { label: 'Calendar', route: ROUTES.CALENDAR, icon: 'calendar' },
  { label: 'Settings', route: ROUTES.SETTINGS, icon: 'gear' },
] as const

export type NavIcon = (typeof NAV_ITEMS)[number]['icon']
