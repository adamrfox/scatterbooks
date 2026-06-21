import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createCategory, listCategories } from '../api/categories'
import { createEdition, listEditions } from '../api/editions'
import { createWishListEntry, getWishList, getWishListEntry, updateWishListEntry } from '../api/wishLists'
import {
  deleteWishListEntryImage,
  listWishListEntryImages,
  reorderWishListEntryImage,
  uploadWishListEntryImage,
  wishListEntryImageFullUrl,
  wishListEntryImageThumbUrl,
} from '../api/wishListEntryImages'
import { ApiError } from '../api/client'
import { ComboboxWithAdd } from '../components/ComboboxWithAdd'
import { ImageGallery } from '../components/ImageGallery'
import { ImagePicker } from '../components/ImagePicker'
import { StagedPhotoPicker, type StagedImage } from '../components/StagedPhotoPicker'
import { useAuth } from '../context/AuthContext'

export function WishListEntryFormPage() {
  const { id, entryId } = useParams<{ id: string; entryId: string }>()
  const wishListId = Number(id)
  const isEdit = entryId !== undefined
  const entryIdParam = isEdit ? Number(entryId) : null
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user } = useAuth()

  const [title, setTitle] = useState('')
  const [author, setAuthor] = useState('')
  const [categoryId, setCategoryId] = useState<number | null>(null)
  const [editionId, setEditionId] = useState<number | null>(null)
  const [notes, setNotes] = useState('')
  const [year, setYear] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [savedEntryId, setSavedEntryId] = useState<number | null>(entryIdParam)
  const [stagedImages, setStagedImages] = useState<StagedImage[]>([])

  const stagedImagesRef = useRef<StagedImage[]>(stagedImages)

  useEffect(() => {
    stagedImagesRef.current = stagedImages
  }, [stagedImages])

  useEffect(() => {
    return () => {
      stagedImagesRef.current.forEach((image) => URL.revokeObjectURL(image.previewUrl))
    }
  }, [])

  const {
    data: wishList,
    isLoading: wishListLoading,
    isError: wishListError,
  } = useQuery({
    queryKey: ['wish-list', wishListId],
    queryFn: () => getWishList(wishListId),
    enabled: Number.isFinite(wishListId),
  })

  const { data: existingEntry } = useQuery({
    queryKey: ['wish-list-entry', wishListId, entryIdParam],
    queryFn: () => getWishListEntry(wishListId, entryIdParam as number),
    enabled: isEdit && entryIdParam !== null,
  })

  const { data: categories = [] } = useQuery({ queryKey: ['categories'], queryFn: listCategories })
  const { data: editions = [] } = useQuery({ queryKey: ['editions'], queryFn: listEditions })

  const { data: existingImages = [] } = useQuery({
    queryKey: ['wish-list-entry-images', wishListId, savedEntryId],
    queryFn: () => listWishListEntryImages(wishListId, savedEntryId as number),
    enabled: savedEntryId !== null,
  })

  // One-time sync of fetched record into editable local form state, not a
  // cascading update -- existingEntry only changes once the query resolves.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (existingEntry) {
      setTitle(existingEntry.title)
      setAuthor(existingEntry.author)
      setCategoryId(existingEntry.category_id)
      setEditionId(existingEntry.edition_id)
      setNotes(existingEntry.notes ?? '')
      setYear(existingEntry.year != null ? String(existingEntry.year) : '')
    }
  }, [existingEntry])
  /* eslint-enable react-hooks/set-state-in-effect */

  const createCategoryMutation = useMutation({
    mutationFn: createCategory,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['categories'] }),
  })
  const createEditionMutation = useMutation({
    mutationFn: createEdition,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['editions'] }),
  })

  function addStagedImages(files: File[]) {
    const additions = files.map((file) => ({
      id: crypto.randomUUID(),
      file,
      previewUrl: URL.createObjectURL(file),
    }))
    setStagedImages((previous) => [...previous, ...additions])
  }

  function removeStagedImage(id: string) {
    setStagedImages((previous) => {
      const target = previous.find((image) => image.id === id)
      if (target) URL.revokeObjectURL(target.previewUrl)
      return previous.filter((image) => image.id !== id)
    })
  }

  function moveStagedImage(id: string, direction: -1 | 1) {
    setStagedImages((previous) => {
      const index = previous.findIndex((image) => image.id === id)
      const targetIndex = index + direction
      if (index === -1 || targetIndex < 0 || targetIndex >= previous.length) return previous
      const next = [...previous]
      const [moved] = next.splice(index, 1)
      next.splice(targetIndex, 0, moved)
      return next
    })
  }

  function clearStagedImages() {
    stagedImagesRef.current.forEach((image) => URL.revokeObjectURL(image.previewUrl))
    setStagedImages([])
  }

  const saveMutation = useMutation({
    mutationFn: () => {
      const input = {
        title: title.trim(),
        author: author.trim(),
        category_id: categoryId,
        edition_id: editionId,
        notes: notes.trim() ? notes.trim() : null,
        year: year.trim() ? Number(year.trim()) : null,
      }
      return savedEntryId
        ? updateWishListEntry(wishListId, savedEntryId, input)
        : createWishListEntry(wishListId, input)
    },
    onSuccess: async (entry) => {
      queryClient.invalidateQueries({ queryKey: ['wish-list-entries', wishListId] })
      queryClient.invalidateQueries({ queryKey: ['wish-list-entry', wishListId, entry.id] })
      setError(null)

      if (!isEdit) {
        setSavedEntryId(entry.id)

        if (stagedImages.length > 0) {
          const uploadErrors: string[] = []
          for (const staged of stagedImages) {
            try {
              await uploadWishListEntryImage(wishListId, entry.id, staged.file)
            } catch (uploadError) {
              const message =
                uploadError instanceof ApiError ? String(uploadError.detail) : 'upload failed'
              uploadErrors.push(`${staged.file.name}: ${message}`)
            }
          }
          clearStagedImages()
          queryClient.invalidateQueries({
            queryKey: ['wish-list-entry-images', wishListId, entry.id],
          })
          if (uploadErrors.length > 0) {
            setError(`Saved, but some photos failed to upload: ${uploadErrors.join('; ')}`)
            navigate(`/wish-lists/${wishListId}/entries/${entry.id}/edit`, { replace: true })
            return
          }
        }
      }

      navigate(`/wish-lists/${wishListId}`)
    },
    onError: (err) => {
      setError(err instanceof ApiError ? String(err.detail) : 'Could not save.')
    },
  })

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    saveMutation.mutate()
  }

  if (wishListLoading) return <p className="text-gray-500">Loading...</p>

  const canEdit = !!user && !!wishList && (user.role === 'admin' || wishList.owner_id === user.id)
  if (wishListError || !wishList || !canEdit) {
    return (
      <p className="p-8 text-center text-gray-500">You don&apos;t have permission to view this page.</p>
    )
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-4 text-xl font-semibold text-gray-900">
        {isEdit ? 'Edit wish list entry' : `Add to ${wishList?.name ?? 'wish list'}`}
      </h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="title" className="block text-sm font-medium text-gray-700">
            Title
          </label>
          <input
            id="title"
            type="text"
            required
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-base focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label htmlFor="author" className="block text-sm font-medium text-gray-700">
            Author
          </label>
          <input
            id="author"
            type="text"
            required
            value={author}
            onChange={(event) => setAuthor(event.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-base focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label htmlFor="year" className="block text-sm font-medium text-gray-700">
            Year
          </label>
          <input
            id="year"
            type="number"
            inputMode="numeric"
            value={year}
            onChange={(event) => setYear(event.target.value)}
            className="mt-1 block w-32 rounded-md border border-gray-300 px-3 py-2 text-base focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <ComboboxWithAdd
            id="category"
            label="Category"
            items={categories}
            value={categoryId}
            onChange={setCategoryId}
            onCreate={(name) => createCategoryMutation.mutateAsync(name)}
            isCreating={createCategoryMutation.isPending}
          />
          <ComboboxWithAdd
            id="edition"
            label="Edition"
            items={editions}
            value={editionId}
            onChange={setEditionId}
            onCreate={(name) => createEditionMutation.mutateAsync(name)}
            isCreating={createEditionMutation.isPending}
          />
        </div>

        <div>
          <label htmlFor="notes" className="block text-sm font-medium text-gray-700">
            Notes
          </label>
          <textarea
            id="notes"
            rows={4}
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-base focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex gap-2">
          <button
            type="submit"
            disabled={saveMutation.isPending}
            className="rounded-md bg-indigo-600 px-4 py-2 text-base font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {saveMutation.isPending ? 'Saving...' : 'Save'}
          </button>
          {savedEntryId && (
            <button
              type="button"
              onClick={() => navigate(`/wish-lists/${wishListId}/entries/${savedEntryId}`)}
              className="rounded-md border border-gray-300 px-4 py-2 text-base text-gray-700 hover:bg-gray-50"
            >
              Done
            </button>
          )}
        </div>
      </form>

      <div className="mt-8">
        <h2 className="mb-2 text-sm font-medium text-gray-700">Photos</h2>
        {savedEntryId ? (
          <>
            <ImagePicker
              currentCount={existingImages.length}
              upload={(file) => uploadWishListEntryImage(wishListId, savedEntryId, file)}
              onUploaded={() => {
                queryClient.invalidateQueries({
                  queryKey: ['wish-list-entry-images', wishListId, savedEntryId],
                })
                queryClient.invalidateQueries({
                  queryKey: ['wish-list-entry', wishListId, savedEntryId],
                })
              }}
            />
            <div className="mt-3">
              <ImageGallery
                queryKey={['wish-list-entry-images', wishListId, savedEntryId]}
                listImages={() => listWishListEntryImages(wishListId, savedEntryId)}
                deleteImage={(imageId) => deleteWishListEntryImage(wishListId, savedEntryId, imageId)}
                reorderImage={(imageId, position) =>
                  reorderWishListEntryImage(wishListId, savedEntryId, imageId, position)
                }
                thumbUrl={(imageId) => wishListEntryImageThumbUrl(wishListId, savedEntryId, imageId)}
                fullUrl={(imageId) => wishListEntryImageFullUrl(wishListId, savedEntryId, imageId)}
                onChanged={() =>
                  queryClient.invalidateQueries({
                    queryKey: ['wish-list-entry', wishListId, savedEntryId],
                  })
                }
                canEdit
              />
            </div>
          </>
        ) : (
          <StagedPhotoPicker
            images={stagedImages}
            onFilesAccepted={addStagedImages}
            onRemove={removeStagedImage}
            onMove={moveStagedImage}
          />
        )}
      </div>
    </div>
  )
}
