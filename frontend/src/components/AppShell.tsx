import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { roleAtLeast, type Role } from '../types'

interface NavItem {
  label: string
  path: string
  minRole?: Role
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Books', path: '/' },
  { label: 'Categories & Editions', path: '/categories', minRole: 'librarian' },
  { label: 'Users', path: '/admin/users', minRole: 'admin' },
]

export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)

  const visibleItems = NAV_ITEMS.filter(
    (item) => !item.minRole || (user && roleAtLeast(user.role, item.minRole)),
  )

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-6">
            <span className="text-lg font-semibold text-gray-900">scatterbooks</span>
            <nav className="hidden gap-4 md:flex">
              {visibleItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className="text-sm text-gray-600 hover:text-gray-900"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>

          <div className="hidden items-center gap-3 md:flex">
            {user && (
              <>
                <Link to="/account" className="text-sm text-gray-500 hover:text-gray-900">
                  {user.username} <span className="text-gray-400">({user.role})</span>
                </Link>
                <button
                  type="button"
                  onClick={() => logout()}
                  className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100"
                >
                  Log out
                </button>
              </>
            )}
          </div>

          <button
            type="button"
            className="rounded-md p-2 text-gray-600 hover:bg-gray-100 md:hidden"
            aria-label="Toggle menu"
            onClick={() => setMenuOpen((open) => !open)}
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>
        </div>

        {menuOpen && (
          <div className="border-t border-gray-200 px-4 py-3 md:hidden">
            <nav className="flex flex-col gap-3">
              {visibleItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className="text-sm text-gray-600"
                  onClick={() => setMenuOpen(false)}
                >
                  {item.label}
                </Link>
              ))}
            </nav>
            {user && (
              <div className="mt-3 flex items-center justify-between border-t border-gray-100 pt-3">
                <Link
                  to="/account"
                  className="text-sm text-gray-500"
                  onClick={() => setMenuOpen(false)}
                >
                  {user.username} ({user.role})
                </Link>
                <button
                  type="button"
                  onClick={() => logout()}
                  className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700"
                >
                  Log out
                </button>
              </div>
            )}
          </div>
        )}
      </header>

      <main className="mx-auto max-w-5xl px-4 py-6">{children}</main>
    </div>
  )
}
