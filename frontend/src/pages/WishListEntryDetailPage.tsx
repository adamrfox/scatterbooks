import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { deleteWishListEntry, getWishList, getWishListEntry, moveWishListEntryToLibrary } from '../api/wishLists'
import {
  deleteWishListEntryImage,
  listWishListEntryImages,
  reorderWishListEntryImage,
  wishListEntryImageFullUrl,
  wishListEntryImageThumbUrl,
} from '../api/wishListEntryImages'
import { ApiError } from '../api/client'
import { ImageGallery } from '../components/ImageGallery'
import { useAuth } from '../context/AuthContext'

export function WishListEntryDetailPage() {
  const { id, entryId } = useParams<{ id: string; entryId: string }>()
  const wishListId = Number(id)
  const entryIdNum = Number(entryId)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user } = useAuth()

  const { data: wishList } = useQuery({
    queryKey: ['wish-list', wishListId],
    queryFn: () => getWishList(wishListId),
    enabled: Number.isFinite(wishListId),
  })

  const {
    data: entry,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['wish-list-entry', wishListId, entryIdNum],
    queryFn: () => getWishListEntry(wishListId, entryIdNum),
    enabled: Number.isFinite(wishListId) && Number.isFinite(entryIdNum),
  })

  const canEdit = !!user && !!wishList && (user.role === 'admin' || wishList.owner_id === user.id)

  const deleteMutation = useMutation({
    mutationFn: () => deleteWishListEntry(wishListId, entryIdNum),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wish-list-entries', wishListId] })
      navigate(`/wish-lists/${wishListId}`)
    },
  })

  const moveMutation = useMutation({
    mutationFn: () => moveWishListEntryToLibrary(wishListId, entryIdNum),
    onSuccess: (book) => {
      queryClient.invalidateQueries({ queryKey: ['wish-list-entries', wishListId] })
      queryClient.invalidateQueries({ queryKey: ['books'] })
      navigate(`/books/${book.id}`)
    },
  })

  if (isLoading) return <p className="text-gray-500">Loading...</p>
  if (isError || !entry || !wishList) {
    return (
      <p className="p-8 text-center text-gray-500">You don&apos;t have permission to view this page.</p>
    )
  }

  return (
    <div>
      <Link to={`/wish-lists/${wishListId}`} className="text-sm text-indigo-600 hover:underline">
        &larr; Back to {wishList.name}
      </Link>

      <div className="mt-3 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">{entry.title}</h1>
          <p className="text-gray-600">
            {entry.author}
            {entry.year != null && <span className="text-gray-400"> &middot; {entry.year}</span>}
          </p>
        </div>
        {canEdit && (
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => moveMutation.mutate()}
              disabled={moveMutation.isPending}
              className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {moveMutation.isPending ? 'Moving...' : 'Move to library'}
            </button>
            <Link
              to={`/wish-lists/${wishListId}/entries/${entry.id}/edit`}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
            >
              Edit
            </Link>
            <button
              type="button"
              onClick={() => {
                if (window.confirm(`Delete "${entry.title}"? This cannot be undone.`)) {
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

      {moveMutation.isError && (
        <p className="mt-2 text-sm text-red-600">
          {moveMutation.error instanceof ApiError
            ? String(moveMutation.error.detail)
            : 'Could not move to library.'}
        </p>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        {entry.category && (
          <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs text-indigo-700">
            {entry.category.name}
          </span>
        )}
        {entry.edition && (
          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-700">
            {entry.edition.name}
          </span>
        )}
      </div>

      {entry.notes && <p className="mt-4 whitespace-pre-wrap text-gray-700">{entry.notes}</p>}

      <div className="mt-6">
        <h2 className="mb-2 text-sm font-medium text-gray-700">Photos</h2>
        <ImageGallery
          queryKey={['wish-list-entry-images', wishListId, entry.id]}
          listImages={() => listWishListEntryImages(wishListId, entry.id)}
          deleteImage={(imageId) => deleteWishListEntryImage(wishListId, entry.id, imageId)}
          reorderImage={(imageId, position) =>
            reorderWishListEntryImage(wishListId, entry.id, imageId, position)
          }
          thumbUrl={(imageId) => wishListEntryImageThumbUrl(wishListId, entry.id, imageId)}
          fullUrl={(imageId) => wishListEntryImageFullUrl(wishListId, entry.id, imageId)}
          onChanged={() =>
            queryClient.invalidateQueries({ queryKey: ['wish-list-entry', wishListId, entry.id] })
          }
          canEdit={canEdit}
        />
      </div>
    </div>
  )
}
