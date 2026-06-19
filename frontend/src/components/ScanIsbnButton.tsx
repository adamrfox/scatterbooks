import { useEffect, useRef, useState } from 'react'
import type { IScannerControls } from '@zxing/browser'
import { lookupIsbn } from '../api/isbn'
import { ApiError } from '../api/client'

interface ScanIsbnButtonProps {
  onFound: (result: { title: string | null; author: string | null }) => void
}

function looksLikeIsbn13(value: string): boolean {
  const digits = value.replace(/[^0-9]/g, '')
  return digits.length === 13 && (digits.startsWith('978') || digits.startsWith('979'))
}

export function ScanIsbnButton({ onFound }: ScanIsbnButtonProps) {
  const [open, setOpen] = useState(false)
  const [manualIsbn, setManualIsbn] = useState('')
  const [status, setStatus] = useState<'idle' | 'looking-up' | 'not-found'>('idle')
  const [cameraError, setCameraError] = useState<string | null>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const controlsRef = useRef<IScannerControls | null>(null)

  function stopScanning() {
    controlsRef.current?.stop()
    controlsRef.current = null
  }

  function closeModal() {
    stopScanning()
    setOpen(false)
    setStatus('idle')
    setCameraError(null)
    setManualIsbn('')
  }

  async function handleIsbnCandidate(rawValue: string) {
    if (!looksLikeIsbn13(rawValue)) return
    stopScanning()
    setStatus('looking-up')
    const digits = rawValue.replace(/[^0-9]/g, '')
    try {
      const result = await lookupIsbn(digits)
      onFound({ title: result.title, author: result.author })
      closeModal()
    } catch (error) {
      setStatus('not-found')
      if (!(error instanceof ApiError && error.status === 404)) {
        // Unexpected error (network, 500, etc) -- still just let the user
        // fall back to manual entry rather than surfacing raw error detail.
        console.error('ISBN lookup failed', error)
      }
    }
  }

  function handleManualLookup() {
    void handleIsbnCandidate(manualIsbn)
  }

  useEffect(() => {
    if (!open) return

    let cancelled = false

    // ZXing is a large, pure-JS image-processing library -- dynamically
    // imported so it's only fetched when someone actually opens the
    // scanner, not bundled into every page load.
    Promise.all([import('@zxing/browser'), import('@zxing/library')])
      .then(([{ BrowserMultiFormatReader }, { BarcodeFormat, DecodeHintType }]) => {
        if (cancelled) return

        const reader = new BrowserMultiFormatReader(
          new Map([[DecodeHintType.POSSIBLE_FORMATS, [BarcodeFormat.EAN_13, BarcodeFormat.UPC_A]]]),
        )

        return reader.decodeFromConstraints(
          { video: { facingMode: 'environment' } },
          videoRef.current ?? undefined,
          (result) => {
            if (cancelled || !result) return
            void handleIsbnCandidate(result.getText())
          },
        )
      })
      .then((controls) => {
        if (!controls) return
        if (cancelled) {
          controls.stop()
        } else {
          controlsRef.current = controls
        }
      })
      .catch((error: unknown) => {
        if (cancelled) return
        setCameraError(error instanceof Error ? error.message : 'Could not access the camera.')
      })

    return () => {
      cancelled = true
      stopScanning()
    }
    // Only (re)start scanning when the modal opens/closes -- handleIsbnCandidate
    // is stable enough in practice and re-running this on every render would
    // restart the camera stream constantly.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mb-4 rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
      >
        Scan ISBN barcode
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4">
          <div className="w-full max-w-sm rounded-lg bg-white p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-semibold text-gray-900">Scan ISBN barcode</h2>
              <button type="button" onClick={closeModal} className="text-sm text-gray-500">
                Cancel
              </button>
            </div>

            {cameraError ? (
              <p className="mb-3 text-sm text-red-600">{cameraError}</p>
            ) : (
              <video ref={videoRef} className="mb-3 w-full rounded-md bg-black" muted playsInline />
            )}

            {status === 'looking-up' && <p className="mb-3 text-sm text-gray-500">Looking up...</p>}
            {status === 'not-found' && (
              <p className="mb-3 text-sm text-red-600">
                No match found for that ISBN -- you can enter details manually.
              </p>
            )}

            <p className="mb-1 text-sm text-gray-700">Or enter the ISBN manually:</p>
            <div className="flex gap-2">
              <input
                type="text"
                inputMode="numeric"
                value={manualIsbn}
                onChange={(event) => setManualIsbn(event.target.value)}
                placeholder="978..."
                className="block w-full rounded-md border border-gray-300 px-3 py-2 text-base focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
              <button
                type="button"
                onClick={handleManualLookup}
                disabled={status === 'looking-up'}
                className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                Look up
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
