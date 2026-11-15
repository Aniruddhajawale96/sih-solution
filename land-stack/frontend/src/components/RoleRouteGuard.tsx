import { Navigate } from 'react-router-dom'
import { useAuthStore, type Role } from '@/store/authStore'
interface Props { allowed: Role[]; children: React.ReactNode }
export function RoleRouteGuard({ allowed, children }: Props) {
  const role = useAuthStore(s => s.role)
  if (!role) return <Navigate to="/citizen/dashboard" replace />
  if (!allowed.includes(role)) return <Navigate to="/" replace />
  return <>{children}</>
}
