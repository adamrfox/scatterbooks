import { useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { uploadBookImage } from '../api/images'
import { ApiError } from '../api/client'

interface ImagePickerProps {
  bookId: number
  currentCount: number
  maxCount?: number
}

export function ImagePicker({ bookId, currentCount, maxCount = 5 }: ImagePickerProps) {
  const queryClient = useQueryClient()
  const cameraInputRef = useRef<HTMLInputElement>(null)
  const libraryInputRef = useRef<HTMLInputElement>(null)
  const [errors, setErrors] = useState<string[]>([])

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadBookImage(bookId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['book-images', bookId] })
      queryClient.invalidateQueries({ queryKey: ['book', bookId] })
    },
  })

  const remaining = maxCount - currentCount
  const disabled = remaining <= 0

  async function handleFiles(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return
    setErrors([])
    const files = Array.from(fileList).slice(0, Math.max(remaining, 0))
    for (const file of files) {
      try {
        await uploadMutation.mutateAsync(file)
      } catch (error) {
        const message = error instanceof ApiError ? String(error.detail) : 'Upload failed'
        setErrors((previous) => [...previous, `${file.name}: ${message}`])
      }
    }
  }

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={disabled}
          onClick={() => cameraInputRef.current?.click()}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
        >
          Take Photo
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => libraryInputRef.current?.click()}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
        >
          Choose from Library
        </button>
        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={(event) => {
            void handleFiles(event.target.files)
            event.target.value = ''
          }}
        />
        <input
          ref={libraryInputRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={(event) => {
            void handleFiles(event.target.files)
            event.target.value = ''
          }}
        />
      </div>
      <p className="mt-1 text-xs text-gray-500">
        {disabled
          ? 'Maximum of 5 photos reached.'
          : `${remaining} of ${maxCount} photo slots remaining.`}
      </p>
      {uploadMutation.isPending && <p className="mt-1 text-xs text-gray-500">Uploading...</p>}
      {errors.length > 0 && (
        <ul className="mt-1 space-y-0.5 text-xs text-red-600">
          {errors.map((message, index) => (
            <li key={index}>{message}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
