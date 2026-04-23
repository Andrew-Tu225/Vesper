export const ROUTES = {
  LOGIN: '/login',
  AUTH_CALLBACK: '/auth/callback',
  DASHBOARD: '/dashboard',
  ONBOARDING: '/onboarding',
  QUEUE: '/queue',
  CALENDAR: '/calendar',
  STYLE_LIBRARY: '/style-library',
  CHANNEL_SETUP: '/channel-setup',
  SETTINGS: '/settings',
} as const

export const NAV_ITEMS = [
  { label: 'Dashboard', route: ROUTES.DASHBOARD, icon: 'home' },
  { label: 'Queue', route: ROUTES.QUEUE, icon: 'inbox' },
  { label: 'Calendar', route: ROUTES.CALENDAR, icon: 'calendar' },
  { label: 'Style Library', route: ROUTES.STYLE_LIBRARY, icon: 'sparkle' },
  { label: 'Settings', route: ROUTES.SETTINGS, icon: 'gear' },
] as const

export type NavIcon = (typeof NAV_ITEMS)[number]['icon']
