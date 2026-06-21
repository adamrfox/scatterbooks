import { useState } from 'react'
import { PhotoCaptureButtons } from './PhotoCaptureButtons'
import { identifyCoverPhoto } from '../api/coverIdentification'
import { ApiError } from '../api/client'

interface IdentifyFromPhotoButtonProps {
  onFound: (result: { title: string | null; author: string | null }) => void
  onPhotoAccepted: (file: File) => void
}

export function IdentifyFromPhotoButton({ onFound, onPhotoAccepted }: IdentifyFromPhotoButtonProps) {
  const [open, setOpen] = useState(false)
  const [status, setStatus] = useState<'idle' | 'identifying' | 'not-found'>('idle')
  const [error, setError] = useState<string | null>(null)

  function closeModal() {
    setOpen(false)
    setStatus('idle')
    setError(null)
  }

  async function handleFilesSelected(files: File[]) {
    const file = files[0]
    if (!file) return

    setStatus('identifying')
    setError(null)
    try {
      const result = await identifyCoverPhoto(file)
      if (!result.title && !result.author) {
        setStatus('not-found')
        return
      }
      // A successful identification means this is a real photo of the book's
      // cover -- keep it as one of the book's photos, not just a throwaway
      // input to the lookup.
      onPhotoAccepted(file)
      onFound({ title: result.title, author: result.author })
      closeModal()
    } catch (err) {
      setStatus('not-found')
      setError(err instanceof ApiError ? String(err.detail) : 'Could not identify the book.')
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mb-4 rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
      >
        Identify from photo
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4">
          <div className="w-full max-w-sm rounded-lg bg-white p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-semibold text-gray-900">Identify from photo</h2>
              <button type="button" onClick={closeModal} className="text-sm text-gray-500">
                Cancel
              </button>
            </div>

            <p className="mb-3 text-sm text-gray-500">
              Take or choose a photo of the cover. This sends the photo to Claude (Anthropic) to
              suggest a title and author -- always double-check before saving. If it's
              recognized, the photo is kept as one of the book's photos (you can remove it
              later).
            </p>

            <PhotoCaptureButtons
              disabled={status === 'identifying'}
              remaining={1}
              maxCount={1}
              onFilesSelected={(files) => void handleFilesSelected(files)}
              helperText={status === 'identifying' ? undefined : 'Pick one photo of the cover.'}
            />

            {status === 'identifying' && <p className="mt-3 text-sm text-gray-500">Identifying...</p>}
            {status === 'not-found' && (
              <p className="mt-3 text-sm text-red-600">
                {error ?? "Couldn't identify that cover -- you can enter details manually."}
              </p>
            )}
          </div>
        </div>
      )}
    </>
  )
}
