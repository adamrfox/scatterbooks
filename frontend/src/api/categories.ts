import { apiClient } from './client'
import type { Category } from '../types'

export function listCategories(): Promise<Category[]> {
  return apiClient.get<Category[]>('/api/categories')
}

export function createCategory(name: string): Promise<Category> {
  return apiClient.post<Category>('/api/categories', { name })
}

export function renameCategory(id: number, name: string): Promise<Category> {
  return apiClient.patch<Category>(`/api/categories/${id}`, { name })
}

export function deleteCategory(id: number): Promise<void> {
  return apiClient.delete<void>(`/api/categories/${id}`)
}
