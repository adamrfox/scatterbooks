import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createUser, deactivateUser, listUsers, updateUser, type UpdateUserInput } from '../api/users'
import { ApiError } from '../api/client'
import { useAuth } from '../context/AuthContext'
import type { Role } from '../types'

const ROLES: Role[] = ['user', 'librarian', 'admin']

function describeError(err: unknown): string {
  return err instanceof ApiError ? String(err.detail) : 'Something went wrong.'
}

export function UserManagementPage() {
  const { user: currentUser } = useAuth()
  const queryClient = useQueryClient()
  const { data: users = [], isLoading } = useQuery({ queryKey: ['users'], queryFn: listUsers })

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<Role>('user')
  const [createError, setCreateError] = useState<string | null>(null)
  const [rowError, setRowError] = useState<string | null>(null)
  const [resetPasswordForId, setResetPasswordForId] = useState<number | null>(null)
  const [resetPasswordValue, setResetPasswordValue] = useState('')

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['users'] })
  }

  const createMutation = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      invalidate()
      setUsername('')
      setPassword('')
      setRole('user')
      setCreateError(null)
    },
    onError: (err) => setCreateError(describeError(err)),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, input }: { id: number; input: UpdateUserInput }) => updateUser(id, input),
    onSuccess: () => {
      invalidate()
      setRowError(null)
    },
    onError: (err) => setRowError(describeError(err)),
  })

  const deactivateMutation = useMutation({
    mutationFn: deactivateUser,
    onSuccess: () => {
      invalidate()
      setRowError(null)
    },
    onError: (err) => setRowError(describeError(err)),
  })

  function handleCreate(event: FormEvent) {
    event.preventDefault()
    if (!username.trim() || password.length < 8) {
      setCreateError('Username is required and password must be at least 8 characters.')
      return
    }
    createMutation.mutate({ username: username.trim(), password, role })
  }

  function handleRoleChange(id: number, newRole: Role) {
    updateMutation.mutate({ id, input: { role: newRole } })
  }

  function handleDeactivate(id: number, name: string) {
    if (window.confirm(`Deactivate "${name}"? They won't be able to log in until reactivated.`)) {
      deactivateMutation.mutate(id)
    }
  }

  function handleReactivate(id: number) {
    updateMutation.mutate({ id, input: { is_active: true } })
  }

  function handleResetPassword(id: number) {
    if (resetPasswordValue.length < 8) {
      setRowError('New password must be at least 8 characters.')
      return
    }
    updateMutation.mutate(
      { id, input: { password: resetPasswordValue } },
      {
        onSuccess: () => {
          invalidate()
          setResetPasswordForId(null)
          setResetPasswordValue('')
          setRowError(null)
        },
      },
    )
  }

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-4 text-xl font-semibold text-gray-900">Users</h1>

      <form
        onSubmit={handleCreate}
        className="mb-6 flex flex-wrap items-end gap-2 rounded-md border border-gray-200 p-4"
      >
        <div>
          <label htmlFor="new-username" className="block text-sm font-medium text-gray-700">
            Username
          </label>
          <input
            id="new-username"
            type="text"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            className="mt-1 block rounded-md border border-gray-300 px-3 py-2 text-base focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label htmlFor="new-password" className="block text-sm font-medium text-gray-700">
            Temporary password
          </label>
          <input
            id="new-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="mt-1 block rounded-md border border-gray-300 px-3 py-2 text-base focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label htmlFor="new-role" className="block text-sm font-medium text-gray-700">
            Role
          </label>
          <select
            id="new-role"
            value={role}
            onChange={(event) => setRole(event.target.value as Role)}
            className="mt-1 block rounded-md border border-gray-300 px-3 py-2 text-base focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            {ROLES.map((roleOption) => (
              <option key={roleOption} value={roleOption}>
                {roleOption}
              </option>
            ))}
          </select>
        </div>
        <button
          type="submit"
          disabled={createMutation.isPending}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          Create user
        </button>
      </form>
      {createError && <p className="mb-4 text-sm text-red-600">{createError}</p>}
      {rowError && <p className="mb-4 text-sm text-red-600">{rowError}</p>}

      <div className="overflow-x-auto rounded-md border border-gray-200">
        <table className="w-full text-left text-sm">
          <thead className="bg-gray-50 text-gray-500">
            <tr>
              <th className="px-3 py-2">Username</th>
              <th className="px-3 py-2">Role</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {users.map((rowUser) => {
              const isSelf = rowUser.id === currentUser?.id
              return (
                <tr key={rowUser.id}>
                  <td className="whitespace-nowrap px-3 py-2 text-gray-900">
                    {rowUser.username} {isSelf && <span className="text-gray-400">(you)</span>}
                  </td>
                  <td className="px-3 py-2">
                    <select
                      value={rowUser.role}
                      disabled={isSelf}
                      onChange={(event) => handleRoleChange(rowUser.id, event.target.value as Role)}
                      className="rounded-md border border-gray-300 px-2 py-1 text-sm disabled:opacity-50"
                    >
                      {ROLES.map((roleOption) => (
                        <option key={roleOption} value={roleOption}>
                          {roleOption}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-3 py-2">
                    {rowUser.is_active ? (
                      <span className="text-green-700">Active</span>
                    ) : (
                      <span className="text-gray-400">Deactivated</span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap items-center gap-2">
                      {resetPasswordForId === rowUser.id ? (
                        <>
                          <input
                            type="password"
                            placeholder="New password"
                            value={resetPasswordValue}
                            onChange={(event) => setResetPasswordValue(event.target.value)}
                            className="rounded-md border border-gray-300 px-2 py-1 text-sm"
                          />
                          <button
                            type="button"
                            onClick={() => handleResetPassword(rowUser.id)}
                            className="text-indigo-600"
                          >
                            Save
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setResetPasswordForId(null)
                              setResetPasswordValue('')
                            }}
                            className="text-gray-500"
                          >
                            Cancel
                          </button>
                        </>
                      ) : (
                        <button
                          type="button"
                          onClick={() => {
                            setResetPasswordForId(rowUser.id)
                            setResetPasswordValue('')
                          }}
                          className="text-indigo-600"
                        >
                          Reset password
                        </button>
                      )}
                      {rowUser.is_active ? (
                        <button
                          type="button"
                          disabled={isSelf}
                          onClick={() => handleDeactivate(rowUser.id, rowUser.username)}
                          className="text-red-600 disabled:opacity-30"
                        >
                          Deactivate
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => handleReactivate(rowUser.id)}
                          className="text-green-700"
                        >
                          Reactivate
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {!isLoading && users.length === 0 && (
          <p className="px-3 py-4 text-sm text-gray-500">No users yet.</p>
        )}
      </div>
    </div>
  )
}
