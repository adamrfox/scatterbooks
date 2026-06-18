import { apiClient } from './client'
import type { Edition } from '../types'

export function listEditions(): Promise<Edition[]> {
  return apiClient.get<Edition[]>('/api/editions')
}

export function createEdition(name: string): Promise<Edition> {
  return apiClient.post<Edition>('/api/editions', { name })
}

export function renameEdition(id: number, name: string): Promise<Edition> {
  return apiClient.patch<Edition>(`/api/editions/${id}`, { name })
}

export function deleteEdition(id: number): Promise<void> {
  return apiClient.delete<void>(`/api/editions/${id}`)
}
