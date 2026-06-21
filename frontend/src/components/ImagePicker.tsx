import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { ApiError } from '../api/client'
import { PhotoCaptureButtons } from './PhotoCaptureButtons'

interface ImagePickerProps {
  currentCount: number
  maxCount?: number
  upload: (file: File) => Promise<unknown>
  onUploaded: () => void
}

export function ImagePicker({ currentCount, maxCount = 5, upload, onUploaded }: ImagePickerProps) {
  const [errors, setErrors] = useState<string[]>([])

  const uploadMutation = useMutation({
    mutationFn: upload,
    onSuccess: onUploaded,
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
