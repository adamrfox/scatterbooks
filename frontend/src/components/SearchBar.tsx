import type { Category, Edition } from '../types'

interface SearchBarProps {
  q: string
  onQChange: (q: string) => void
  categoryId: number | null
  onCategoryChange: (id: number | null) => void
  editionId: number | null
  onEditionChange: (id: number | null) => void
  categories: Category[]
  editions: Edition[]
}

export function SearchBar({
  q,
  onQChange,
  categoryId,
  onCategoryChange,
  editionId,
  onEditionChange,
  categories,
  editions,
}: SearchBarProps) {
  return (
    <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center">
      <input
        type="search"
        value={q}
        onChange={(event) => onQChange(event.target.value)}
        placeholder="Search title, author, or notes..."
        className="block w-full rounded-md border border-gray-300 px-3 py-2 text-base focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 sm:flex-1"
      />
      <select
        value={categoryId ?? ''}
        onChange={(event) => onCategoryChange(event.target.value ? Number(event.target.value) : null)}
        className="block w-full rounded-md border border-gray-300 px-3 py-2 text-base focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 sm:w-44"
      >
        <option value="">All categories</option>
        {categories.map((category) => (
          <option key={category.id} value={category.id}>
            {category.name}
          </option>
        ))}
      </select>
      <select
        value={editionId ?? ''}
        onChange={(event) => onEditionChange(event.target.value ? Number(event.target.value) : null)}
        className="block w-full rounded-md border border-gray-300 px-3 py-2 text-base focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 sm:w-44"
      >
        <option value="">All editions</option>
        {editions.map((edition) => (
          <option key={edition.id} value={edition.id}>
            {edition.name}
          </option>
        ))}
      </select>
    </div>
  )
}
