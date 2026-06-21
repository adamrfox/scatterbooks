import { apiClient } from './client'
import type { Book } from '../types'

export interface BookListParams {
  q?: string
  category_id?: number
  edition_id?: number
  limit?: number
  offset?: number
}

function toQueryString(params: BookListParams): string {
  const search = new URLSearchParams()
  if (params.q) search.set('q', params.q)
  if (params.category_id != null) search.set('category_id', String(params.category_id))
  if (params.edition_id != null) search.set('edition_id', String(params.edition_id))
  if (params.limit != null) search.set('limit', String(params.limit))
  if (params.offset != null) search.set('offset', String(params.offset))
  const query = search.toString()
  return query ? `?${query}` : ''
}

export function listBooks(params: BookListParams = {}): Promise<Book[]> {
  return apiClient.get<Book[]>(`/api/books${toQueryString(params)}`)
}

export function getBook(id: number): Promise<Book> {
  return apiClient.get<Book>(`/api/books/${id}`)
}

export interface BookInput {
  title: string
  author: string
  category_id: number | null
  edition_id: number | null
  notes: string | null
  year: number | null
}

export function createBook(input: BookInput): Promise<Book> {
  return apiClient.post<Book>('/api/books', input)
}

export function updateBook(id: number, input: Partial<BookInput>): Promise<Book> {
  return apiClient.patch<Book>(`/api/books/${id}`, input)
}

export function deleteBook(id: number): Promise<void> {
  return apiClient.delete<void>(`/api/books/${id}`)
}
