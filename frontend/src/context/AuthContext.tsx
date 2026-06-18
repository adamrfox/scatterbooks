import { createContext, useContext, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { login as apiLogin, logout as apiLogout, me as apiMe } from '../api/auth'
import { ApiError } from '../api/client'
import type { User } from '../types'

interface AuthContextValue {
  user: User | null
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  loginError: string | null
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

const ME_QUERY_KEY = ['auth', 'me']

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()

  const { data: user, isLoading } = useQuery({
    queryKey: ME_QUERY_KEY,
    queryFn: async (): Promise<User | null> => {
      try {
        return await apiMe()
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          return null
        }
        throw error
      }
    },
    retry: false,
    staleTime: 60_000,
  })

  const loginMutation = useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) =>
      apiLogin(username, password),
    onSuccess: (loggedInUser) => {
      queryClient.setQueryData(ME_QUERY_KEY, loggedInUser)
    },
  })

  const logoutMutation = useMutation({
    mutationFn: apiLogout,
    onSuccess: () => {
      queryClient.setQueryData(ME_QUERY_KEY, null)
    },
  })

  const loginError = loginMutation.error
    ? loginMutation.error instanceof ApiError
      ? String(loginMutation.error.detail ?? loginMutation.error.message)
      : 'Something went wrong. Please try again.'
    : null

  const value: AuthContextValue = {
    user: user ?? null,
    isLoading,
    loginError,
    login: async (username, password) => {
      await loginMutation.mutateAsync({ username, password })
    },
    logout: async () => {
      await logoutMutation.mutateAsync()
    },
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components -- hook belongs with its provider
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
