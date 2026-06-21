import { apiClient } from './client'

export interface IdentifyCoverResult {
  title: string | null
  author: string | null
}

export function identifyCoverPhoto(file: File): Promise<IdentifyCoverResult> {
  const formData = new FormData()
  formData.append('file', file)
  return apiClient.post<IdentifyCoverResult>('/api/identify-cover', formData)
}
