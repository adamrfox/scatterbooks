import { useRef } from 'react'

interface PhotoCaptureButtonsProps {
  disabled: boolean
  remaining: number
  maxCount: number
  onFilesSelected: (files: File[]) => void
  helperText?: string
}

export function PhotoCaptureButtons({
  disabled,
  remaining,
  maxCount,
  onFilesSelected,
  helperText,
}: PhotoCaptureButtonsProps) {
  const cameraInputRef = useRef<HTMLInputElement>(null)
  const libraryInputRef = useRef<HTMLInputElement>(null)

  function handleChange(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return
    onFilesSelected(Array.from(fileList))
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
            handleChange(event.target.files)
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
            handleChange(event.target.files)
            event.target.value = ''
          }}
        />
      </div>
      <p className="mt-1 text-xs text-gray-500">
        {helperText ??
          (disabled
            ? `Maximum of ${maxCount} photos reached.`
            : `${remaining} of ${maxCount} photo slots remaining.`)}
      </p>
    </div>
  )
}
