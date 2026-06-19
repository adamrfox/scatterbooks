import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getSettings, updateGoogleBooksApiKey } from '../api/settings'
import { ApiError } from '../api/client'

function describeSource(source: string): string {
  switch (source) {
    case 'database':
      return 'Configured here in the app.'
    case 'environment':
      return 'Configured via the GOOGLE_BOOKS_API_KEY environment variable.'
    default:
      return 'Not configured -- ISBN scans will only use Open Library.'
  }
}

export function SettingsPage() {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['settings'], queryFn: getSettings })

  const [newKey, setNewKey] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: (key: string | null) => updateGoogleBooksApiKey(key),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      setNewKey('')
      setError(null)
    },
    onError: (err) => {
      setSuccess(null)
      setError(err instanceof ApiError ? String(err.detail) : 'Could not save the API key.')
    },
  })

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!newKey.trim()) {
      setError('Enter a key, or use Clear to remove a previously saved one.')
      return
    }
    setSuccess(null)
    setError(null)
    mutation.mutate(newKey.trim(), { onSuccess: () => setSuccess('API key saved.') })
  }

  function handleClear() {
    setSuccess(null)
    setError(null)
    mutation.mutate(null, { onSuccess: () => setSuccess('API key cleared.') })
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="mb-1 text-xl font-semibold text-gray-900">Settings</h1>
      <p className="mb-4 text-sm text-gray-500">App-wide configuration for this deployment.</p>

      <h2 className="mb-1 text-sm font-medium text-gray-700">Google Books API key</h2>
      <p className="mb-3 text-sm text-gray-500">
        Optional fallback for the "scan ISBN" lookup when Open Library doesn&apos;t have a match.
      </p>

      {isLoading ? (
        <p className="text-sm text-gray-500">Loading...</p>
      ) : (
        <>
          <p className="mb-3 text-sm text-gray-700">{describeSource(data?.google_books_api_key_source ?? 'none')}</p>

          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label htmlFor="google-books-key" className="block text-sm font-medium text-gray-700">
                {data?.google_books_api_key_configured ? 'Replace key' : 'Set key'}
              </label>
              <input
                id="google-books-key"
                type="password"
                autoComplete="off"
                value={newKey}
                onChange={(event) => setNewKey(event.target.value)}
                placeholder="Paste your API key"
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-base focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            {error && <p className="text-sm text-red-600">{error}</p>}
            {success && <p className="text-sm text-green-700">{success}</p>}

            <div className="flex gap-2">
              <button
                type="submit"
                disabled={mutation.isPending}
                className="rounded-md bg-indigo-600 px-4 py-2 text-base font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {mutation.isPending ? 'Saving...' : 'Save'}
              </button>
              {data?.google_books_api_key_source === 'database' && (
                <button
                  type="button"
                  onClick={handleClear}
                  disabled={mutation.isPending}
                  className="rounded-md border border-gray-300 px-4 py-2 text-base text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                >
                  Clear
                </button>
              )}
            </div>
          </form>
        </>
      )}
    </div>
  )
}
