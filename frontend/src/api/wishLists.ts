import { apiClient } from './client'
import type { Book, WishList, WishListEntry } from '../types'

export interface WishListInput {
  name: string
  is_public: boolean
}

export function listWishLists(): Promise<WishList[]> {
  return apiClient.get<WishList[]>('/api/wish-lists')
}

export function getWishList(id: number): Promise<WishList> {
  return apiClient.get<WishList>(`/api/wish-lists/${id}`)
}

export function createWishList(input: WishListInput): Promise<WishList> {
  return apiClient.post<WishList>('/api/wish-lists', input)
}

export function updateWishList(id: number, input: Partial<WishListInput>): Promise<WishList> {
  return apiClient.patch<WishList>(`/api/wish-lists/${id}`, input)
}

export function deleteWishList(id: number): Promise<void> {
  return apiClient.delete<void>(`/api/wish-lists/${id}`)
}

export interface WishListEntryInput {
  title: string
  author: string
  category_id: number | null
  edition_id: number | null
  notes: string | null
  year: number | null
}

export function listWishListEntries(wishListId: number): Promise<WishListEntry[]> {
  return apiClient.get<WishListEntry[]>(`/api/wish-lists/${wishListId}/entries`)
}

export function getWishListEntry(wishListId: number, entryId: number): Promise<WishListEntry> {
  return apiClient.get<WishListEntry>(`/api/wish-lists/${wishListId}/entries/${entryId}`)
}

export function createWishListEntry(
  wishListId: number,
  input: WishListEntryInput,
): Promise<WishListEntry> {
  return apiClient.post<WishListEntry>(`/api/wish-lists/${wishListId}/entries`, input)
}

export function updateWishListEntry(
  wishListId: number,
  entryId: number,
  input: Partial<WishListEntryInput>,
): Promise<WishListEntry> {
  return apiClient.patch<WishListEntry>(`/api/wish-lists/${wishListId}/entries/${entryId}`, input)
}

export function deleteWishListEntry(wishListId: number, entryId: number): Promise<void> {
  return apiClient.delete<void>(`/api/wish-lists/${wishListId}/entries/${entryId}`)
}

export function moveWishListEntryToLibrary(wishListId: number, entryId: number): Promise<Book> {
  return apiClient.post<Book>(
    `/api/wish-lists/${wishListId}/entries/${entryId}/move-to-library`,
  )
}
