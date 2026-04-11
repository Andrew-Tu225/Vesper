import { NavLink } from 'react-router-dom'
import { NavIconSvg } from './icons'
import type { NavIcon } from '@/lib/constants'

interface Props {
  label: string
  route: string
  icon: NavIcon
}

export function SidebarNavItem({ label, route, icon }: Props) {
  return (
    <NavLink
      to={route}
      className={({ isActive }) =>
        `sidebar__nav-item${isActive ? ' sidebar__nav-item--active' : ''}`
      }
    >
      <NavIconSvg name={icon} />
      {label}
    </NavLink>
  )
}
