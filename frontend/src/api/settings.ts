import { apiClient } from './client'

export interface AppSettings {
  google_books_api_key_configured: boolean
  google_books_api_key_source: 'database' | 'environment' | 'none'
}

export function getSettings(): Promise<AppSettings> {
  return apiClient.get<AppSettings>('/api/settings')
}

export function updateGoogleBooksApiKey(key: string | null): Promise<AppSettings> {
  return apiClient.patch<AppSettings>('/api/settings', { google_books_api_key: key })
}
