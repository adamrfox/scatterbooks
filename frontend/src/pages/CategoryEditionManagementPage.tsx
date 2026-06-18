import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createCategory, deleteCategory, listCategories, renameCategory } from '../api/categories'
import { createEdition, deleteEdition, listEditions, renameEdition } from '../api/editions'
import { ApiError } from '../api/client'
import type { Category, Edition } from '../types'

type Tab = 'categories' | 'editions'

export function CategoryEditionManagementPage() {
  const [tab, setTab] = useState<Tab>('categories')

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="mb-4 text-xl font-semibold text-gray-900">Categories &amp; Editions</h1>
      <div className="mb-4 flex gap-4 border-b border-gray-200">
        <button
          type="button"
          onClick={() => setTab('categories')}
          className={`-mb-px border-b-2 px-1 py-2 text-sm font-medium ${
            tab === 'categories'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-gray-500'
          }`}
        >
          Categories
        </button>
        <button
          type="button"
          onClick={() => setTab('editions')}
          className={`-mb-px border-b-2 px-1 py-2 text-sm font-medium ${
            tab === 'editions'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-gray-500'
          }`}
        >
          Editions
        </button>
      </div>

      {tab === 'categories' ? <CategoryManager /> : <EditionManager />}
    </div>
  )
}

function CategoryManager() {
  const queryClient = useQueryClient()
  const { data: categories = [] } = useQuery({ queryKey: ['categories'], queryFn: listCategories })

  const createMutation = useMutation({
    mutationFn: createCategory,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['categories'] }),
  })
  const renameMutation = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) => renameCategory(id, name),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['categories'] }),
  })
  const deleteMutation = useMutation({
    mutationFn: deleteCategory,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['categories'] }),
  })

  return (
    <ManagedList
      items={categories}
      onCreate={(name) => createMutation.mutateAsync(name)}
      onRename={(id, name) => renameMutation.mutateAsync({ id, name })}
      onDelete={(id) => deleteMutation.mutateAsync(id)}
      noun="category"
    />
  )
}

function EditionManager() {
  const queryClient = useQueryClient()
  const { data: editions = [] } = useQuery({ queryKey: ['editions'], queryFn: listEditions })

  const createMutation = useMutation({
    mutationFn: createEdition,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['editions'] }),
  })
  const renameMutation = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) => renameEdition(id, name),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['editions'] }),
  })
  const deleteMutation = useMutation({
    mutationFn: deleteEdition,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['editions'] }),
  })

  return (
    <ManagedList
      items={editions}
      onCreate={(name) => createMutation.mutateAsync(name)}
      onRename={(id, name) => renameMutation.mutateAsync({ id, name })}
      onDelete={(id) => deleteMutation.mutateAsync(id)}
      noun="edition"
    />
  )
}

interface ManagedListProps {
  items: (Category | Edition)[]
  onCreate: (name: string) => Promise<unknown>
  onRename: (id: number, name: string) => Promise<unknown>
  onDelete: (id: number) => Promise<unknown>
  noun: string
}

function ManagedList({ items, onCreate, onRename, onDelete, noun }: ManagedListProps) {
  const [newName, setNewName] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editingName, setEditingName] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function handleCreate(event: FormEvent) {
    event.preventDefault()
    const name = newName.trim()
    if (!name) return
    setError(null)
    try {
      await onCreate(name)
      setNewName('')
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function handleRename(id: number) {
    const name = editingName.trim()
    if (!name) return
    setError(null)
    try {
      await onRename(id, name)
      setEditingId(null)
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function handleDelete(id: number) {
    setError(null)
    try {
      await onDelete(id)
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <div>
      <form onSubmit={handleCreate} className="mb-4 flex gap-2">
        <input
          type="text"
          value={newName}
          onChange={(event) => setNewName(event.target.value)}
          placeholder={`New ${noun} name`}
          className="block w-full rounded-md border border-gray-300 px-3 py-2 text-base focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
        <button
          type="submit"
          className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          Add
        </button>
      </form>

      {error && <p className="mb-2 text-sm text-red-600">{error}</p>}

      <ul className="divide-y divide-gray-200 rounded-md border border-gray-200">
        {items.map((item) => (
          <li key={item.id} className="flex items-center justify-between gap-2 px-3 py-2">
            {editingId === item.id ? (
              <>
                <input
                  type="text"
                  autoFocus
                  value={editingName}
                  onChange={(event) => setEditingName(event.target.value)}
                  className="block w-full rounded-md border border-gray-300 px-2 py-1 text-sm"
                />
                <button type="button" onClick={() => handleRename(item.id)} className="text-sm text-indigo-600">
                  Save
                </button>
                <button type="button" onClick={() => setEditingId(null)} className="text-sm text-gray-500">
                  Cancel
                </button>
              </>
            ) : (
              <>
                <span className="text-gray-900">{item.name}</span>
                <div className="flex gap-3 text-sm">
                  <button
                    type="button"
                    onClick={() => {
                      setEditingId(item.id)
                      setEditingName(item.name)
                    }}
                    className="text-indigo-600"
                  >
                    Rename
                  </button>
                  <button type="button" onClick={() => handleDelete(item.id)} className="text-red-600">
                    Delete
                  </button>
                </div>
              </>
            )}
          </li>
        ))}
        {items.length === 0 && <li className="px-3 py-2 text-sm text-gray-500">No {noun}s yet.</li>}
      </ul>
    </div>
  )
}

function describeError(err: unknown): string {
  return err instanceof ApiError ? String(err.detail) : 'Something went wrong.'
}
