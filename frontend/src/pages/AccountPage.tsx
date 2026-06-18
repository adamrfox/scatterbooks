import { useState, type FormEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
import { changeOwnPassword } from '../api/users'
import { ApiError } from '../api/client'
import { useAuth } from '../context/AuthContext'

export function AccountPage() {
  const { user } = useAuth()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const mutation = useMutation({
    mutationFn: () => changeOwnPassword(currentPassword, newPassword),
    onSuccess: () => {
      setSuccess(true)
      setError(null)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    },
    onError: (err) => {
      setSuccess(false)
      setError(err instanceof ApiError ? String(err.detail) : 'Could not change password.')
    },
  })

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSuccess(false)
    if (newPassword.length < 8) {
      setError('New password must be at least 8 characters.')
      return
    }
    if (newPassword !== confirmPassword) {
      setError('New passwords do not match.')
      return
    }
    setError(null)
    mutation.mutate()
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="mb-1 text-xl font-semibold text-gray-900">My account</h1>
      <p className="mb-4 text-sm text-gray-500">
        Signed in as <strong>{user?.username}</strong> ({user?.role})
      </p>

      <h2 className="mb-2 text-sm font-medium text-gray-700">Change password</h2>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label htmlFor="current-password" className="block text-sm font-medium text-gray-700">
            Current password
          </label>
          <input
            id="current-password"
            type="password"
            autoComplete="current-password"
            required
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-base focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label htmlFor="new-password" className="block text-sm font-medium text-gray-700">
            New password
          </label>
          <input
            id="new-password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-base focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label htmlFor="confirm-password" className="block text-sm font-medium text-gray-700">
            Confirm new password
          </label>
          <input
            id="confirm-password"
            type="password"
            autoComplete="new-password"
            required
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-base focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {success && <p className="text-sm text-green-700">Password changed.</p>}
        <button
          type="submit"
          disabled={mutation.isPending}
          className="rounded-md bg-indigo-600 px-4 py-2 text-base font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {mutation.isPending ? 'Saving...' : 'Change password'}
        </button>
      </form>
    </div>
  )
}
