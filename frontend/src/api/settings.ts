import { apiClient } from './client'

export type KeySource = 'database' | 'environment' | 'none'

export interface PublicSettings {
  library_name: string
}

export interface AppSettings extends PublicSettings {
  google_books_api_key_configured: boolean
  google_books_api_key_source: KeySource
  anthropic_api_key_configured: boolean
  anthropic_api_key_source: KeySource
}

export function getPublicSettings(): Promise<PublicSettings> {
  return apiClient.get<PublicSettings>('/api/settings/public')
}

export function getSettings(): Promise<AppSettings> {
  return apiClient.get<AppSettings>('/api/settings')
}

export function updateLibraryName(name: string): Promise<AppSettings> {
  return apiClient.patch<AppSettings>('/api/settings', { library_name: name })
}

export function updateGoogleBooksApiKey(key: string | null): Promise<AppSettings> {
  return apiClient.patch<AppSettings>('/api/settings', { google_books_api_key: key })
}

export function updateAnthropicApiKey(key: string | null): Promise<AppSettings> {
  return apiClient.patch<AppSettings>('/api/settings', { anthropic_api_key: key })
}
