import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { uploadBookImage } from '../api/images'
import { ApiError } from '../api/client'
import { PhotoCaptureButtons } from './PhotoCaptureButtons'

interface ImagePickerProps {
  bookId: number
  currentCount: number
  maxCount?: number
}

export function ImagePicker({ bookId, currentCount, maxCount = 5 }: ImagePickerProps) {
  const queryClient = useQueryClient()
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

  async function handleFilesSelected(files: File[]) {
    setErrors([])
    const limited = files.slice(0, Math.max(remaining, 0))
    for (const file of limited) {
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
      <PhotoCaptureButtons
        disabled={disabled}
        remaining={remaining}
        maxCount={maxCount}
        onFilesSelected={(files) => void handleFilesSelected(files)}
      />
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
