import { apiClient } from './client'
import type { BookImage } from '../types'

export function listBookImages(bookId: number): Promise<BookImage[]> {
  return apiClient.get<BookImage[]>(`/api/books/${bookId}/images`)
}

export function uploadBookImage(bookId: number, file: File): Promise<BookImage> {
  const formData = new FormData()
  formData.append('file', file)
  return apiClient.post<BookImage>(`/api/books/${bookId}/images`, formData)
}

export function reorderBookImage(bookId: number, imageId: number, position: number): Promise<BookImage> {
  return apiClient.patch<BookImage>(`/api/books/${bookId}/images/${imageId}`, { position })
}

export function deleteBookImage(bookId: number, imageId: number): Promise<void> {
  return apiClient.delete<void>(`/api/books/${bookId}/images/${imageId}`)
}

export function bookImageThumbUrl(bookId: number, imageId: number): string {
  return `/api/books/${bookId}/images/${imageId}/thumb`
}

export function bookImageFullUrl(bookId: number, imageId: number): string {
  return `/api/books/${bookId}/images/${imageId}`
}
