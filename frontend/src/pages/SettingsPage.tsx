import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getSettings, updateAnthropicApiKey, updateGoogleBooksApiKey } from '../api/settings'
import { ApiKeyField } from '../components/ApiKeyField'

export function SettingsPage() {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['settings'], queryFn: getSettings })

  function invalidate() {
    return queryClient.invalidateQueries({ queryKey: ['settings'] })
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="mb-1 text-xl font-semibold text-gray-900">Settings</h1>
      <p className="mb-6 text-sm text-gray-500">App-wide configuration for this deployment.</p>

      {isLoading || !data ? (
        <p className="text-sm text-gray-500">Loading...</p>
      ) : (
        <div className="space-y-8">
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
