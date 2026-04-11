import { NAV_ITEMS } from '@/lib/constants'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import { useLogout } from '@/hooks/useLogout'
import { SidebarNavItem } from './SidebarNavItem'

export function Sidebar() {
  const { data: user } = useCurrentUser()
  const logout = useLogout()

  const initial = user?.email?.[0]?.toUpperCase() ?? '?'

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <span className="sidebar__brand-name">Vesper</span>
      </div>

      <nav className="sidebar__nav" aria-label="Main navigation">
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
            {logout.isPending ? '…' : 'Out'}
          </button>
        </div>
      )}
    </aside>
  )
}
