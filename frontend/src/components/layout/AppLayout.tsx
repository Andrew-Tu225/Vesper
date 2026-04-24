import { useState, useCallback } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { NAV_ITEMS } from '@/lib/constants'
import './layout.css'

function usePageTitle() {
  const { pathname } = useLocation()
  return NAV_ITEMS.find(item => item.route === pathname)?.label ?? 'Vesper'
}

function HamburgerIcon({ isOpen }: { isOpen: boolean }) {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      {isOpen ? (
        <path d="M4 4l12 12M16 4L4 16" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
      ) : (
        <path d="M3 5.5h14M3 10h14M3 14.5h14" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
      )}
    </svg>
  )
}

export function AppLayout() {
  const pageTitle = usePageTitle()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const closeSidebar = useCallback(() => setSidebarOpen(false), [])

  return (
    <div className="app-layout">
      {sidebarOpen && (
        <div
          className="sidebar-backdrop"
          onClick={closeSidebar}
          aria-hidden="true"
        />
      )}

      <Sidebar isOpen={sidebarOpen} onClose={closeSidebar} />

      <div className="main-wrapper">
        <header className="topbar">
          <button
            className="topbar__hamburger"
            onClick={() => setSidebarOpen(o => !o)}
            aria-label={sidebarOpen ? 'Close navigation' : 'Open navigation'}
            aria-expanded={sidebarOpen}
          >
            <HamburgerIcon isOpen={sidebarOpen} />
          </button>
          <span className="topbar__title">{pageTitle}</span>
        </header>
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}