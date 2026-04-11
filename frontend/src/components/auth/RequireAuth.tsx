import { Navigate, useLocation } from 'react-router-dom'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import { ROUTES } from '@/lib/constants'
import { Spinner } from '@/components/ui/Spinner'
import '@/components/ui/ui.css'

interface Props {
  children: React.ReactNode
}

export function RequireAuth({ children }: Props) {
  const { data: user, isLoading, isFetched } = useCurrentUser()
  const location = useLocation()

  if (isLoading || !isFetched) {
    return (
      <div className="full-loading">
        <Spinner size="lg" />
      </div>
    )
  }

  if (!user) {
    return <Navigate to={ROUTES.LOGIN} state={{ from: location }} replace />
  }

  return <>{children}</>
}
