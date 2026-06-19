import { apiClient } from './client'

export interface IsbnLookupResult {
  isbn: string
  title: string | null
  author: string | null
}

export function lookupIsbn(isbn: string): Promise<IsbnLookupResult> {
  return apiClient.get<IsbnLookupResult>(`/api/isbn/${encodeURIComponent(isbn)}`)
}
