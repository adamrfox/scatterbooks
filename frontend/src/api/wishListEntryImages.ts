import { apiClient } from './client'
import type { WishListEntryImage } from '../types'

function basePath(wishListId: number, entryId: number): string {
  return `/api/wish-lists/${wishListId}/entries/${entryId}/images`
}

export function listWishListEntryImages(
  wishListId: number,
  entryId: number,
): Promise<WishListEntryImage[]> {
  return apiClient.get<WishListEntryImage[]>(basePath(wishListId, entryId))
}

export function uploadWishListEntryImage(
  wishListId: number,
  entryId: number,
  file: File,
): Promise<WishListEntryImage> {
  const formData = new FormData()
  formData.append('file', file)
  return apiClient.post<WishListEntryImage>(basePath(wishListId, entryId), formData)
}

export function reorderWishListEntryImage(
  wishListId: number,
  entryId: number,
  imageId: number,
  position: number,
): Promise<WishListEntryImage> {
  return apiClient.patch<WishListEntryImage>(`${basePath(wishListId, entryId)}/${imageId}`, {
    position,
  })
}

export function deleteWishListEntryImage(
  wishListId: number,
  entryId: number,
  imageId: number,
): Promise<void> {
  return apiClient.delete<void>(`${basePath(wishListId, entryId)}/${imageId}`)
}

export function wishListEntryImageThumbUrl(
  wishListId: number,
  entryId: number,
  imageId: number,
): string {
  return `${basePath(wishListId, entryId)}/${imageId}/thumb`
}

export function wishListEntryImageFullUrl(
  wishListId: number,
  entryId: number,
  imageId: number,
): string {
  return `${basePath(wishListId, entryId)}/${imageId}`
}
