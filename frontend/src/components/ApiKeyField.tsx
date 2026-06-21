import { useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import type { KeySource } from '../api/settings'

interface ApiKeyFieldProps {
  id: string
  label: string
  description: string
  configured: boolean
  source: KeySource
  notConfiguredText: string
  onSave: (key: string) => Promise<unknown>
  onClear: () => Promise<unknown>
}

export function ApiKeyField({
  id,
  label,
  description,
  configured,
  source,
  notConfiguredText,
  onSave,
  onClear,
}: ApiKeyFieldProps) {
  const [newKey, setNewKey] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  function describeSource(): string {
    if (source === 'database') return 'Configured here in the app.'
    if (source === 'environment') return 'Configured via an environment variable.'
    return notConfiguredText
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!newKey.trim()) {
      setError('Enter a key, or use Clear to remove a previously saved one.')
      return
    }
    setError(null)
    setSuccess(null)
    setSaving(true)
    try {
      await onSave(newKey.trim())
      setNewKey('')
      setSuccess('API key saved.')
    } catch (err) {
      setError(err instanceof ApiError ? String(err.detail) : 'Could not save the API key.')
    } finally {
      setSaving(false)
    }
  }

  async function handleClear() {
    setError(null)
    setSuccess(null)
    setSaving(true)
    try {
      await onClear()
      setSuccess('API key cleared.')
    } catch (err) {
      setError(err instanceof ApiError ? String(err.detail) : 'Could not clear the API key.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <h2 className="mb-1 text-sm font-medium text-gray-700">{label}</h2>
      <p className="mb-3 text-sm text-gray-500">{description}</p>
      <p className="mb-3 text-sm text-gray-700">{describeSource()}</p>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label htmlFor={id} className="block text-sm font-medium text-gray-700">
            {configured ? 'Replace key' : 'Set key'}
          </label>
          <input
            id={id}
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
            disabled={saving}
            className="rounded-md bg-indigo-600 px-4 py-2 text-base font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
          {source === 'database' && (
            <button
              type="button"
              onClick={() => void handleClear()}
              disabled={saving}
              className="rounded-md border border-gray-300 px-4 py-2 text-base text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              Clear
            </button>
          )}
        </div>
      </form>
    </div>
  )
}
