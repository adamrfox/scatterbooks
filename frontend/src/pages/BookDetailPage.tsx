import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { deleteBook, getBook } from '../api/books'
import { bookImageFullUrl, bookImageThumbUrl, deleteBookImage, listBookImages, reorderBookImage } from '../api/images'
import { ImageGallery } from '../components/ImageGallery'
import { useAuth } from '../context/AuthContext'
import { roleAtLeast } from '../types'

export function BookDetailPage() {
  const { id } = useParams<{ id: string }>()
  const bookId = Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const canEdit = !!user && roleAtLeast(user.role, 'librarian')

  const {
    data: book,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['book', bookId],
    queryFn: () => getBook(bookId),
    enabled: Number.isFinite(bookId),
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteBook(bookId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['books'] })
      navigate('/')
    },
  })

  if (isLoading) return <p className="text-gray-500">Loading...</p>
  if (isError || !book) return <p className="text-red-600">Book not found.</p>

  return (
    <div>
      <Link to="/" className="text-sm text-indigo-600 hover:underline">
        &larr; Back to books
      </Link>

      <div className="mt-3 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">{book.title}</h1>
          <p className="text-gray-600">
            {book.author}
            {book.year != null && <span className="text-gray-400"> &middot; {book.year}</span>}
          </p>
        </div>
        {canEdit && (
          <div className="flex gap-2">
            <Link
              to={`/books/${book.id}/edit`}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
            >
              Edit
            </Link>
            <button
              type="button"
              onClick={() => {
                if (window.confirm(`Delete "${book.title}"? This cannot be undone.`)) {
                  deleteMutation.mutate()
                }
              }}
              className="rounded-md border border-red-300 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50"
            >
              Delete
            </button>
          </div>
        )}
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {book.category && (
          <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs text-indigo-700">
            {book.category.name}
          </span>
        )}
        {book.edition && (
          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-700">
            {book.edition.name}
          </span>
        )}
      </div>

      {book.notes && <p className="mt-4 whitespace-pre-wrap text-gray-700">{book.notes}</p>}

      <div className="mt-6">
        <h2 className="mb-2 text-sm font-medium text-gray-700">Photos</h2>
        <ImageGallery
          queryKey={['book-images', book.id]}
          listImages={() => listBookImages(book.id)}
          deleteImage={(imageId) => deleteBookImage(book.id, imageId)}
          reorderImage={(imageId, position) => reorderBookImage(book.id, imageId, position)}
          thumbUrl={(imageId) => bookImageThumbUrl(book.id, imageId)}
          fullUrl={(imageId) => bookImageFullUrl(book.id, imageId)}
          onChanged={() => queryClient.invalidateQueries({ queryKey: ['book', book.id] })}
          canEdit={canEdit}
        />
      </div>
    </div>
  )
}
