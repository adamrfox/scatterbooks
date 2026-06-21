import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

interface GalleryImage {
  id: number
  position: number
}

interface ImageGalleryProps {
  queryKey: unknown[]
  listImages: () => Promise<GalleryImage[]>
  deleteImage: (imageId: number) => Promise<void>
  reorderImage: (imageId: number, position: number) => Promise<unknown>
  thumbUrl: (imageId: number) => string
  fullUrl: (imageId: number) => string
  canEdit: boolean
  onChanged?: () => void
}

export function ImageGallery({
  queryKey,
  listImages,
  deleteImage,
  reorderImage,
  thumbUrl,
  fullUrl,
  canEdit,
  onChanged,
}: ImageGalleryProps) {
  const queryClient = useQueryClient()
  const [lightboxImage, setLightboxImage] = useState<GalleryImage | null>(null)

  const { data: images = [], isLoading } = useQuery({ queryKey, queryFn: listImages })

  function invalidate() {
    queryClient.invalidateQueries({ queryKey })
    onChanged?.()
  }

  const deleteMutation = useMutation({
    mutationFn: (imageId: number) => deleteImage(imageId),
    onSuccess: invalidate,
  })

  const reorderMutation = useMutation({
    mutationFn: ({ imageId, position }: { imageId: number; position: number }) =>
      reorderImage(imageId, position),
    onSuccess: invalidate,
  })

  if (isLoading) {
    return <p className="text-sm text-gray-500">Loading photos...</p>
  }

  if (images.length === 0) {
    return <p className="text-sm text-gray-500">No photos yet.</p>
  }

  function moveImage(index: number, direction: -1 | 1) {
    const target = images[index + direction]
    if (!target) return
    reorderMutation.mutate({ imageId: images[index].id, position: target.position })
  }

  return (
    <>
      <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-5">
        {images.map((image, index) => (
          <div key={image.id} className="relative">
            <button
              type="button"
              onClick={() => setLightboxImage(image)}
              className="block aspect-square w-full overflow-hidden rounded-md bg-gray-100"
            >
              <img src={thumbUrl(image.id)} alt="" className="h-full w-full object-cover" />
            </button>
            {canEdit && (
              <div className="mt-1 flex items-center justify-between text-xs">
                <button
                  type="button"
                  disabled={index === 0}
                  onClick={() => moveImage(index, -1)}
                  className="text-gray-500 disabled:opacity-30"
                  aria-label="Move earlier"
                >
                  &larr;
                </button>
                <button
                  type="button"
                  onClick={() => deleteMutation.mutate(image.id)}
                  className="text-red-600"
                >
                  Delete
                </button>
                <button
                  type="button"
                  disabled={index === images.length - 1}
                  onClick={() => moveImage(index, 1)}
                  className="text-gray-500 disabled:opacity-30"
                  aria-label="Move later"
                >
                  &rarr;
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {lightboxImage && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
          onClick={() => setLightboxImage(null)}
        >
          <img src={fullUrl(lightboxImage.id)} alt="" className="max-h-full max-w-full rounded-md" />
        </div>
      )}
    </>
  )
}
