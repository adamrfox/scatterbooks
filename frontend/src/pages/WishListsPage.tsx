import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createWishList, listWishLists } from '../api/wishLists'
import { ApiError } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { roleAtLeast } from '../types'

export function WishListsPage() {
  const { user } = useAuth()
  const canCreate = !!user && roleAtLeast(user.role, 'librarian')
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newName, setNewName] = useState('')
  const [newIsPublic, setNewIsPublic] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { data: wishLists = [], isLoading } = useQuery({
    queryKey: ['wish-lists'],
    queryFn: listWishLists,
  })

  const createMutation = useMutation({
    mutationFn: () => createWishList({ name: newName.trim(), is_public: newIsPublic }),
    onSuccess: (wishList) => {
      queryClient.invalidateQueries({ queryKey: ['wish-lists'] })
      navigate(`/wish-lists/${wishList.id}`)
    },
    onError: (err) => {
      setError(err instanceof ApiError ? String(err.detail) : 'Could not create wish list.')
    },
  })

  function handleCreate(event: FormEvent) {
    event.preventDefault()
    if (!newName.trim()) return
    setError(null)
    createMutation.mutate()
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Wish Lists</h1>
        {canCreate && !showCreateForm && (
          <button
            type="button"
            onClick={() => setShowCreateForm(true)}
            className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            + New wish list
          </button>
        )}
      </div>

      {showCreateForm && (
        <form
          onSubmit={handleCreate}
          className="mb-4 space-y-3 rounded-md border border-gray-200 p-3"
        >
          <div>
            <label htmlFor="new-wish-list-name" className="block text-sm font-medium text-gray-700">
              Name
            </label>
            <input
              id="new-wish-list-name"
              type="text"
              autoFocus
              required
              value={newName}
              onChange={(event) => setNewName(event.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-base focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={newIsPublic}
              onChange={(event) => setNewIsPublic(event.target.checked)}
            />
            Public (visible to everyone, not just you and admins)
          </label>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="rounded-md bg-indigo-600 px-4 py-2 text-base font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {createMutation.isPending ? 'Creating...' : 'Create'}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowCreateForm(false)
                setNewName('')
                setNewIsPublic(false)
                setError(null)
              }}
              className="rounded-md border border-gray-300 px-4 py-2 text-base text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {isLoading && <p className="text-gray-500">Loading...</p>}

      {!isLoading && wishLists.length === 0 && (
        <p className="text-gray-500">No wish lists yet.</p>
      )}

      <div className="space-y-2">
        {wishLists.map((wishList) => (
          <Link
            key={wishList.id}
            to={`/wish-lists/${wishList.id}`}
            className="block rounded-lg border border-gray-200 bg-white p-3 shadow-sm hover:shadow"
          >
            <div className="flex items-center justify-between">
              <span className="font-medium text-gray-900">{wishList.name}</span>
              <span
                className={
                  wishList.is_public
                    ? 'rounded-full bg-green-50 px-2 py-0.5 text-xs text-green-700'
                    : 'rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-700'
                }
              >
                {wishList.is_public ? 'Public' : 'Private'}
              </span>
            </div>
            <p className="mt-1 text-sm text-gray-500">
              {wishList.entry_count} {wishList.entry_count === 1 ? 'book' : 'books'}
              {user && wishList.owner_id !== user.id && ` -- by ${wishList.owner_username}`}
            </p>
          </Link>
        ))}
      </div>
    </div>
  )
}
