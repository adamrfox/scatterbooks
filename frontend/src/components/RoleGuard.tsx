import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { roleAtLeast, type Role } from '../types'

export function RoleGuard({ minRole, children }: { minRole?: Role; children: ReactNode }) {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return <div className="p-8 text-center text-gray-500">Loading...</div>
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  if (minRole && !roleAtLeast(user.role, minRole)) {
    return (
      <div className="p-8 text-center text-gray-500">
        You don&apos;t have permission to view this page.
      </div>
    )
  }

  return <>{children}</>
}
