import { Route, Routes } from 'react-router-dom'
import { ROUTES } from '@/lib/constants'
import { AppLayout } from '@/components/layout/AppLayout'
import { RequireAuth } from '@/components/auth/RequireAuth'
import Landing from '@/pages/Landing'
import PrivacyPolicy from '@/pages/PrivacyPolicy'
import TermsOfService from '@/pages/TermsOfService'
import Dashboard from '@/pages/Dashboard'
import Onboarding from '@/pages/Onboarding'
import Queue from '@/pages/Queue'
import Calendar from '@/pages/Calendar'
import StyleLibrary from '@/pages/StyleLibrary'
import Settings from '@/pages/Settings'
import NotFound from '@/pages/NotFound'

// TODO: Uncomment when auth is ready
// import Login from '@/pages/Login'
// import OAuthCallback from '@/pages/OAuthCallback'

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/" element={<Landing />} />
      <Route path="/privacy" element={<PrivacyPolicy />} />
      <Route path="/terms" element={<TermsOfService />} />

      {/* TODO: Uncomment when auth/app is ready */}
      {/* <Route path={ROUTES.LOGIN} element={<Login />} />
      <Route path={ROUTES.AUTH_CALLBACK} element={<OAuthCallback />} /> */}

      {/* Protected — wrapped in layout */}
      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route path={ROUTES.DASHBOARD} element={<Dashboard />} />
        <Route path={ROUTES.ONBOARDING} element={<Onboarding />} />
        <Route path={ROUTES.QUEUE} element={<Queue />} />
        <Route path={ROUTES.CALENDAR} element={<Calendar />} />
        <Route path={ROUTES.STYLE_LIBRARY} element={<StyleLibrary />} />
        <Route path={ROUTES.SETTINGS} element={<Settings />} />
      </Route>

      {/* 404 — catches everything else */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
