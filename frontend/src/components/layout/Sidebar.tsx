import { Link } from 'react-router-dom'
import { NAV_ITEMS, ROUTES } from '@/lib/constants'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import { useLogout } from '@/hooks/useLogout'
import { SidebarNavItem } from './SidebarNavItem'

interface SidebarProps {
  isOpen?: boolean
  onClose?: () => void
}

export function Sidebar({ isOpen = false, onClose }: SidebarProps) {
  const { data: user } = useCurrentUser()
  const logout = useLogout()

  const initial = user?.email?.[0]?.toUpperCase() ?? '?'

  return (
    <aside className={`sidebar${isOpen ? ' sidebar--open' : ''}`}>
      <div className="sidebar__brand">
        <Link to={ROUTES.DASHBOARD} onClick={onClose} aria-label="Go to dashboard">
          <img src="/logo.svg" alt="Vesper" className="sidebar__brand-logo" />
        </Link>
      </div>

      <nav className="sidebar__nav" onClick={onClose} aria-label="Main navigation">
        <span className="sidebar__nav-label">Workspace</span>
        {NAV_ITEMS.map((item) => (
          <SidebarNavItem key={item.route} {...item} />
        ))}
      </nav>

      {user && (
        <div className="sidebar__footer">
          <div className="sidebar__avatar">
            {user.avatar_url ? (
              <img src={user.avatar_url} alt={user.display_name ?? user.email} />
            ) : (
              initial
            )}
          </div>
          <div className="sidebar__user-info">
            <div className="sidebar__user-email">{user.email}</div>
          </div>
          <button
            className="sidebar__logout-btn"
            onClick={() => logout.mutate()}
            disabled={logout.isPending}
            aria-label="Log out"
          >
            {logout.isPending ? '…' : 'Sign out'}
          </button>
        </div>
      )}
    </aside>
  )
}