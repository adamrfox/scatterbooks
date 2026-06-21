import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { deleteWishList, getWishList, listWishListEntries, updateWishList } from '../api/wishLists'
import { wishListEntryImageThumbUrl } from '../api/wishListEntryImages'
import { ApiError } from '../api/client'
import { BookPlaceholderIcon } from '../components/BookPlaceholderIcon'
import { useAuth } from '../context/AuthContext'

export function WishListDetailPage() {
  const { id } = useParams<{ id: string }>()
  const wishListId = Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user } = useAuth()

  const [editingName, setEditingName] = useState(false)
  const [nameDraft, setNameDraft] = useState('')
  const [error, setError] = useState<string | null>(null)

  const {
    data: wishList,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['wish-list', wishListId],
    queryFn: () => getWishList(wishListId),
    enabled: Number.isFinite(wishListId),
  })

  const { data: entries = [] } = useQuery({
    queryKey: ['wish-list-entries', wishListId],
    queryFn: () => listWishListEntries(wishListId),
    enabled: Number.isFinite(wishListId) && !!wishList,
  })

  const canEdit = !!user && !!wishList && (user.role === 'admin' || wishList.owner_id === user.id)

  const updateMutation = useMutation({
    mutationFn: (input: { name?: string; is_public?: boolean }) => updateWishList(wishListId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wish-list', wishListId] })
      queryClient.invalidateQueries({ queryKey: ['wish-lists'] })
      setError(null)
    },
    onError: (err) => {
      setError(err instanceof ApiError ? String(err.detail) : 'Could not update wish list.')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteWishList(wishListId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wish-lists'] })
      navigate('/wish-lists')
    },
  })

  if (isLoading) return <p className="text-gray-500">Loading...</p>
  if (isError || !wishList) {
    return (
      <p className="p-8 text-center text-gray-500">You don&apos;t have permission to view this page.</p>
    )
  }

  const startEditingName = () => {
    setNameDraft(wishList.name)
    setEditingName(true)
  }

  const saveName = () => {
    const trimmed = nameDraft.trim()
    if (!trimmed) return
    updateMutation.mutate({ name: trimmed }, { onSuccess: () => setEditingName(false) })
  }

  return (
    <div>
      <Link to="/wish-lists" className="text-sm text-indigo-600 hover:underline">
        &larr; Back to wish lists
      </Link>

      <div className="mt-3 flex flex-wrap items-start justify-between gap-3">
        <div className="flex-1">
          {editingName ? (
            <div className="flex gap-2">
              <input
                type="text"
                autoFocus
                value={nameDraft}
                onChange={(event) => setNameDraft(event.target.value)}
                className="block w-full max-w-sm rounded-md border border-gray-300 px-3 py-2 text-xl font-semibold focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
              <button
                type="button"
                onClick={saveName}
                className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
              >
                Save
              </button>
              <button
                type="button"
                onClick={() => setEditingName(false)}
                className="rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-700"
              >
                Cancel
              </button>
            </div>
          ) : (
            <h1 className="text-2xl font-semibold text-gray-900">
              {wishList.name}
              {canEdit && (
                <button
                  type="button"
                  onClick={startEditingName}
                  className="ml-2 text-sm font-normal text-indigo-600 hover:underline"
                >
                  Rename
                </button>
              )}
            </h1>
          )}
          <p className="text-gray-500">
            {wishList.is_public ? 'Public' : 'Private'}
            {user && wishList.owner_id !== user.id && ` -- by ${wishList.owner_username}`}
          </p>
        </div>
        {canEdit && (
          <div className="flex flex-wrap gap-2">
            <Link
              to={`/wish-lists/${wishList.id}/entries/new`}
              className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
            >
              + Add book
            </Link>
            <button
              type="button"
              onClick={() => updateMutation.mutate({ is_public: !wishList.is_public })}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
            >
              Make {wishList.is_public ? 'private' : 'public'}
            </button>
            <button
              type="button"
              onClick={() => {
                if (window.confirm(`Delete "${wishList.name}"? This cannot be undone.`)) {
                  deleteMutation.mutate()
                }
              }}
              className="rounded-md border border-red-300 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50"
            >
              Delete list
            </button>
          </div>
        )}
      </div>

      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}

      {entries.length === 0 ? (
        <p className="mt-6 text-gray-500">No books on this list yet.</p>
      ) : (
        <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-4">
          {entries.map((entry) => (
            <Link
              key={entry.id}
              to={`/wish-lists/${wishList.id}/entries/${entry.id}`}
              className="flex gap-3 rounded-lg border border-gray-200 bg-white p-3 shadow-sm hover:shadow md:flex-col md:gap-2"
            >
              <div className="h-20 w-16 flex-shrink-0 overflow-hidden rounded-md bg-gray-100 md:h-40 md:w-full">
                {entry.cover_image_id ? (
                  <img
                    src={wishListEntryImageThumbUrl(wishList.id, entry.id, entry.cover_image_id)}
                    alt=""
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="flex h-full w-full items-center justify-center text-gray-300">
                    <BookPlaceholderIcon />
                  </div>
                )}
              </div>
              <div className="flex flex-col justify-center md:justify-start">
                <span className="font-medium text-gray-900">{entry.title}</span>
                <span className="text-sm text-gray-500">
                  {entry.author}
                  {entry.year != null && <span className="text-gray-400"> &middot; {entry.year}</span>}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
