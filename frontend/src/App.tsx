import { Route, Routes } from 'react-router-dom'
import { ROUTES } from '@/lib/constants'
import { AppLayout } from '@/components/layout/AppLayout'
import { RequireAuth } from '@/components/auth/RequireAuth'
import Landing from '@/pages/Landing'
import PrivacyPolicy from '@/pages/PrivacyPolicy'
import TermsOfService from '@/pages/TermsOfService'
import Login from '@/pages/Login'
import OAuthCallback from '@/pages/OAuthCallback'
import Dashboard from '@/pages/Dashboard'
import ChannelSetup from '@/pages/ChannelSetup'
import Onboarding from '@/pages/Onboarding'
import Queue from '@/pages/Queue'
import Calendar from '@/pages/Calendar'
import Settings from '@/pages/Settings'
import NotFound from '@/pages/NotFound'

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/" element={<Landing />} />
      <Route path="/privacy" element={<PrivacyPolicy />} />
      <Route path="/terms" element={<TermsOfService />} />
      <Route path={ROUTES.LOGIN} element={<Login />} />
      <Route path={ROUTES.AUTH_CALLBACK} element={<OAuthCallback />} />

      {/* Protected — wrapped in layout + auth guard */}
      <Route element={<RequireAuth><AppLayout /></RequireAuth>}>
        <Route path={ROUTES.DASHBOARD} element={<Dashboard />} />
        <Route path={ROUTES.CHANNEL_SETUP} element={<ChannelSetup />} />
        <Route path={ROUTES.ONBOARDING} element={<Onboarding />} />
        <Route path={ROUTES.QUEUE} element={<Queue />} />
        <Route path={ROUTES.CALENDAR} element={<Calendar />} />
        <Route path={ROUTES.SETTINGS} element={<Settings />} />
      </Route>

      {/* 404 — catches everything else */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}