import { useState } from 'react'
import { PhotoCaptureButtons } from './PhotoCaptureButtons'

export interface StagedImage {
  id: string
  file: File
  previewUrl: string
}

// Soft client-side check for instant feedback; the server enforces the
// authoritative limit (MAX_UPLOAD_MB) once these are actually uploaded.
const SOFT_MAX_UPLOAD_MB = 15

interface StagedPhotoPickerProps {
  images: StagedImage[]
  onFilesAccepted: (files: File[]) => void
  onRemove: (id: string) => void
  onMove: (id: string, direction: -1 | 1) => void
  maxCount?: number
}

export function StagedPhotoPicker({
  images,
  onFilesAccepted,
  onRemove,
  onMove,
  maxCount = 5,
}: StagedPhotoPickerProps) {
  const [rejected, setRejected] = useState<string[]>([])

  const remaining = maxCount - images.length
  const disabled = remaining <= 0

  function handleFilesSelected(files: File[]) {
    const accepted: File[] = []
    const rejections: string[] = []

    for (const file of files.slice(0, Math.max(remaining, 0))) {
      if (!file.type.startsWith('image/')) {
        rejections.push(`${file.name}: not an image file`)
        continue
      }
      if (file.size > SOFT_MAX_UPLOAD_MB * 1024 * 1024) {
        rejections.push(`${file.name}: exceeds ${SOFT_MAX_UPLOAD_MB}MB`)
        continue
      }
      accepted.push(file)
    }

    setRejected(rejections)
    if (accepted.length > 0) {
      onFilesAccepted(accepted)
    }
  }

  return (
    <div>
      <PhotoCaptureButtons
        disabled={disabled}
        remaining={remaining}
        maxCount={maxCount}
        onFilesSelected={handleFilesSelected}
      />
      {rejected.length > 0 && (
        <ul className="mt-1 space-y-0.5 text-xs text-red-600">
          {rejected.map((message, index) => (
            <li key={index}>{message}</li>
          ))}
        </ul>
      )}

      {images.length > 0 && (
        <div className="mt-3 grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-5">
          {images.map((image, index) => (
            <div key={image.id} className="relative">
              <div className="block aspect-square w-full overflow-hidden rounded-md bg-gray-100">
                <img src={image.previewUrl} alt="" className="h-full w-full object-cover" />
              </div>
              <div className="mt-1 flex items-center justify-between text-xs">
                <button
                  type="button"
                  disabled={index === 0}
                  onClick={() => onMove(image.id, -1)}
                  className="text-gray-500 disabled:opacity-30"
                  aria-label="Move earlier"
                >
                  &larr;
                </button>
                <button type="button" onClick={() => onRemove(image.id)} className="text-red-600">
                  Remove
                </button>
                <button
                  type="button"
                  disabled={index === images.length - 1}
                  onClick={() => onMove(image.id, 1)}
                  className="text-gray-500 disabled:opacity-30"
                  aria-label="Move later"
                >
                  &rarr;
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
