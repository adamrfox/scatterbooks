import { useState, type ChangeEvent } from 'react'

interface ComboboxItem {
  id: number
  name: string
}

interface ComboboxWithAddProps {
  id: string
  label: string
  items: ComboboxItem[]
  value: number | null
  onChange: (id: number | null) => void
  onCreate: (name: string) => Promise<ComboboxItem>
  isCreating?: boolean
  disabled?: boolean
}

const ADD_NEW_VALUE = '__add_new__'

export function ComboboxWithAdd({
  id,
  label,
  items,
  value,
  onChange,
  onCreate,
  isCreating = false,
  disabled = false,
}: ComboboxWithAddProps) {
  const [adding, setAdding] = useState(false)
  const [newName, setNewName] = useState('')
  const [error, setError] = useState<string | null>(null)

  function handleSelectChange(event: ChangeEvent<HTMLSelectElement>) {
    const raw = event.target.value
    if (raw === ADD_NEW_VALUE) {
      setAdding(true)
      setNewName('')
      setError(null)
      return
    }
    onChange(raw === '' ? null : Number(raw))
  }

  async function handleCreate() {
    const name = newName.trim()
    if (!name) return
    setError(null)
    try {
      const created = await onCreate(name)
      onChange(created.id)
      setAdding(false)
      setNewName('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create')
    }
  }

  if (adding) {
    return (
      <div>
        <label htmlFor={`${id}-new-name`} className="block text-sm font-medium text-gray-700">
          {label}
        </label>
        <div className="mt-1 flex gap-2">
          <input
            id={`${id}-new-name`}
            type="text"
            autoFocus
            value={newName}
            onChange={(event) => setNewName(event.target.value)}
            placeholder={`New ${label.toLowerCase()} name`}
            className="block w-full rounded-md border border-gray-300 px-3 py-2 text-base focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
          <button
            type="button"
            onClick={handleCreate}
            disabled={isCreating || !newName.trim()}
            className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            Add
          </button>
          <button
            type="button"
            onClick={() => setAdding(false)}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-700"
          >
            Cancel
          </button>
        </div>
        {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
      </div>
    )
  }

  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-gray-700">
        {label}
      </label>
      <select
        id={id}
        value={value ?? ''}
        onChange={handleSelectChange}
        disabled={disabled}
        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-base focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
      >
        <option value="">None</option>
        {items.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name}
          </option>
        ))}
        <option value={ADD_NEW_VALUE}>+ Add new...</option>
      </select>
    </div>
  )
}
