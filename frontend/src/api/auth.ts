import { apiClient } from './client'
import type { User } from '../types'

export function login(username: string, password: string): Promise<User> {
  return apiClient.post<User>('/api/auth/login', { username, password })
}

export function logout(): Promise<void> {
  return apiClient.post<void>('/api/auth/logout')
}

export function me(): Promise<User> {
  return apiClient.get<User>('/api/auth/me')
}
