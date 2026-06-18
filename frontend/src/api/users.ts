import { apiClient } from './client'
import type { Role, User } from '../types'

export function listUsers(): Promise<User[]> {
  return apiClient.get<User[]>('/api/users')
}

export interface CreateUserInput {
  username: string
  password: string
  role: Role
}

export function createUser(input: CreateUserInput): Promise<User> {
  return apiClient.post<User>('/api/users', input)
}

export interface UpdateUserInput {
  role?: Role
  is_active?: boolean
  password?: string
}

export function updateUser(id: number, input: UpdateUserInput): Promise<User> {
  return apiClient.patch<User>(`/api/users/${id}`, input)
}

export function deactivateUser(id: number): Promise<void> {
  return apiClient.delete<void>(`/api/users/${id}`)
}

export function changeOwnPassword(currentPassword: string, newPassword: string): Promise<void> {
  return apiClient.post<void>('/api/users/me/password', {
    current_password: currentPassword,
    new_password: newPassword,
  })
}
