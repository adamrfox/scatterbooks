import { useState, type FormEvent } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getSettings, updateAnthropicApiKey, updateGoogleBooksApiKey, updateLibraryName } from '../api/settings'
import { ApiKeyField } from '../components/ApiKeyField'

export function SettingsPage() {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['settings'], queryFn: getSettings })
  const [nameInput, setNameInput] = useState<string | null>(null)
  const [nameError, setNameError] = useState<string | null>(null)

  function invalidate() {
    return queryClient.invalidateQueries({ queryKey: ['settings'] })
  }

  function invalidatePublic() {
    return queryClient.invalidateQueries({ queryKey: ['public-settings'] })
  }

  const nameMutation = useMutation({
    mutationFn: (name: string) => updateLibraryName(name),
    onSuccess: () => {
      void invalidate()
      void invalidatePublic()
      setNameInput(null)
      setNameError(null)
    },
    onError: () => setNameError('Could not save library name.'),
  })

  function handleNameSubmit(event: FormEvent) {
    event.preventDefault()
    const trimmed = (nameInput ?? '').trim()
    if (!trimmed) return
    nameMutation.mutate(trimmed)
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="mb-1 text-xl font-semibold text-gray-900">Settings</h1>
      <p className="mb-6 text-sm text-gray-500">App-wide configuration for this deployment.</p>

      {isLoading || !data ? (
        <p className="text-sm text-gray-500">Loading...</p>
      ) : (
        <div className="space-y-8">
          <div>
            <label htmlFor="library-name" className="block text-sm font-medium text-gray-700">
              Library name
            </label>
            <p className="mt-0.5 text-xs text-gray-500">
              Displayed in the header and on the login page. Defaults to &ldquo;scatterbooks&rdquo;.
            </p>
            <form onSubmit={handleNameSubmit} className="mt-2 flex gap-2">
              <input
                id="library-name"
                type="text"
                value={nameInput ?? data.library_name}
                onChange={(e) => setNameInput(e.target.value)}
                maxLength={255}
                className="block w-full rounded-md border border-gray-300 px-3 py-2 text-base focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
              <button
                type="submit"
                disabled={nameMutation.isPending || (nameInput ?? data.library_name) === data.library_name}
                className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {nameMutation.isPending ? 'Saving…' : 'Save'}
              </button>
            </form>
            {nameError && <p className="mt-1 text-xs text-red-600">{nameError}</p>}
          </div>

          <ApiKeyField
            id="google-books-key"
            label="Google Books API key"
            description={'Optional fallback for the "scan ISBN" lookup when Open Library doesn\'t have a match.'}
            configured={data.google_books_api_key_configured}
            source={data.google_books_api_key_source}
            notConfiguredText="Not configured -- ISBN scans will only use Open Library."
            onSave={async (key) => {
              await updateGoogleBooksApiKey(key)
              await invalidate()
            }}
            onClear={async () => {
              await updateGoogleBooksApiKey(null)
              await invalidate()
            }}
          />

          <ApiKeyField
            id="anthropic-key"
            label="Claude (Anthropic) API key"
            description='Enables "Identify from photo" on the add/edit book form -- takes a cover photo and suggests a title/author.'
            configured={data.anthropic_api_key_configured}
            source={data.anthropic_api_key_source}
            notConfiguredText='Not configured -- "Identify from photo" is hidden on the book form.'
            onSave={async (key) => {
              await updateAnthropicApiKey(key)
              await invalidate()
            }}
            onClear={async () => {
              await updateAnthropicApiKey(null)
              await invalidate()
            }}
          />
        </div>
      )}
    </div>
  )
}
