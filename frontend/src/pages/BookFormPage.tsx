import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createBook, getBook, updateBook } from '../api/books'
import { createCategory, listCategories } from '../api/categories'
import { createEdition, listEditions } from '../api/editions'
import { listBookImages, uploadBookImage } from '../api/images'
import { ApiError } from '../api/client'
import { ComboboxWithAdd } from '../components/ComboboxWithAdd'
import { ImageGallery } from '../components/ImageGallery'
import { ImagePicker } from '../components/ImagePicker'
import { ScanIsbnButton } from '../components/ScanIsbnButton'
import { StagedPhotoPicker, type StagedImage } from '../components/StagedPhotoPicker'

export function BookFormPage() {
  const { id } = useParams<{ id: string }>()
  const isEdit = id !== undefined
  const bookId = isEdit ? Number(id) : null
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [title, setTitle] = useState('')
  const [author, setAuthor] = useState('')
  const [categoryId, setCategoryId] = useState<number | null>(null)
  const [editionId, setEditionId] = useState<number | null>(null)
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [savedBookId, setSavedBookId] = useState<number | null>(bookId)
  const [stagedImages, setStagedImages] = useState<StagedImage[]>([])

  // Staged photo preview URLs are created with URL.createObjectURL and must
  // be revoked when no longer needed. A ref (rather than the state directly)
  // lets the unmount cleanup below see the *latest* staged images instead of
  // whatever was staged at mount time.
  const stagedImagesRef = useRef<StagedImage[]>(stagedImages)

  useEffect(() => {
    stagedImagesRef.current = stagedImages
  }, [stagedImages])

  useEffect(() => {
    return () => {
      stagedImagesRef.current.forEach((image) => URL.revokeObjectURL(image.previewUrl))
    }
  }, [])

  const { data: existingBook } = useQuery({
    queryKey: ['book', bookId],
    queryFn: () => getBook(bookId as number),
    enabled: isEdit && bookId !== null,
  })

  const { data: categories = [] } = useQuery({ queryKey: ['categories'], queryFn: listCategories })
  const { data: editions = [] } = useQuery({ queryKey: ['editions'], queryFn: listEditions })

  const { data: existingImages = [] } = useQuery({
    queryKey: ['book-images', savedBookId],
    queryFn: () => listBookImages(savedBookId as number),
    enabled: savedBookId !== null,
  })

  // One-time sync of fetched record into editable local form state, not a
  // cascading update -- existingBook only changes once the query resolves.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (existingBook) {
      setTitle(existingBook.title)
      setAuthor(existingBook.author)
      setCategoryId(existingBook.category_id)
      setEditionId(existingBook.edition_id)
      setNotes(existingBook.notes ?? '')
    }
  }, [existingBook])
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
      }
      return savedBookId ? updateBook(savedBookId, input) : createBook(input)
    },
    onSuccess: async (book) => {
      queryClient.invalidateQueries({ queryKey: ['books'] })
      queryClient.invalidateQueries({ queryKey: ['book', book.id] })
      setError(null)

      if (!isEdit) {
        setSavedBookId(book.id)

        if (stagedImages.length > 0) {
          const uploadErrors: string[] = []
          for (const staged of stagedImages) {
            try {
              await uploadBookImage(book.id, staged.file)
            } catch (uploadError) {
              const message =
                uploadError instanceof ApiError ? String(uploadError.detail) : 'upload failed'
              uploadErrors.push(`${staged.file.name}: ${message}`)
            }
          }
          clearStagedImages()
          queryClient.invalidateQueries({ queryKey: ['book-images', book.id] })
          if (uploadErrors.length > 0) {
            setError(`Book saved, but some photos failed to upload: ${uploadErrors.join('; ')}`)
          }
        }

        navigate(`/books/${book.id}/edit`, { replace: true })
      }
    },
    onError: (err) => {
      setError(err instanceof ApiError ? String(err.detail) : 'Could not save book.')
    },
  })

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    saveMutation.mutate()
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-4 text-xl font-semibold text-gray-900">
        {isEdit ? 'Edit book' : 'Add a book'}
      </h1>
      <ScanIsbnButton
        onFound={({ title: foundTitle, author: foundAuthor }) => {
          if (foundTitle) setTitle(foundTitle)
          if (foundAuthor) setAuthor(foundAuthor)
        }}
      />
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
          {savedBookId && (
            <button
              type="button"
              onClick={() => navigate(`/books/${savedBookId}`)}
              className="rounded-md border border-gray-300 px-4 py-2 text-base text-gray-700 hover:bg-gray-50"
            >
              Done
            </button>
          )}
        </div>
      </form>

      <div className="mt-8">
        <h2 className="mb-2 text-sm font-medium text-gray-700">Photos</h2>
        {savedBookId ? (
          <>
            <ImagePicker bookId={savedBookId} currentCount={existingImages.length} />
            <div className="mt-3">
              <ImageGallery bookId={savedBookId} canEdit />
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
