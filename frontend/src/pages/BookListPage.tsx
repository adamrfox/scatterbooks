import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listBooks } from '../api/books'
import { listCategories } from '../api/categories'
import { listEditions } from '../api/editions'
import { BookCard } from '../components/BookCard'
import { SearchBar } from '../components/SearchBar'
import { useAuth } from '../context/AuthContext'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import { roleAtLeast } from '../types'

export function BookListPage() {
  const { user } = useAuth()
  const canEdit = !!user && roleAtLeast(user.role, 'librarian')

  const [q, setQ] = useState('')
  const [categoryId, setCategoryId] = useState<number | null>(null)
  const [editionId, setEditionId] = useState<number | null>(null)
  const debouncedQ = useDebouncedValue(q, 300)

  const hasActiveFilters = debouncedQ.trim() !== '' || categoryId !== null || editionId !== null

  const { data: categories = [] } = useQuery({ queryKey: ['categories'], queryFn: listCategories })
  const { data: editions = [] } = useQuery({ queryKey: ['editions'], queryFn: listEditions })

  const {
    data: books = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['books', { q: debouncedQ, categoryId, editionId }],
    queryFn: () =>
      listBooks({
        q: debouncedQ.trim() || undefined,
        category_id: categoryId ?? undefined,
        edition_id: editionId ?? undefined,
      }),
  })

  function clearFilters() {
    setQ('')
    setCategoryId(null)
    setEditionId(null)
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Library</h1>
        {canEdit && (
          <Link
            to="/books/new"
            className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            + Add book
          </Link>
        )}
      </div>

      <SearchBar
        q={q}
        onQChange={setQ}
        categoryId={categoryId}
        onCategoryChange={setCategoryId}
        editionId={editionId}
        onEditionChange={setEditionId}
        categories={categories}
        editions={editions}
      />

      {isLoading && <p className="text-gray-500">Loading...</p>}
      {isError && <p className="text-red-600">Could not load books.</p>}

      {!isLoading && books.length === 0 && !hasActiveFilters && (
        <p className="text-gray-500">No books yet{canEdit ? ' -- add your first one.' : '.'}</p>
      )}

      {!isLoading && books.length === 0 && hasActiveFilters && (
        <p className="text-gray-500">
          No books match your search.{' '}
          <button type="button" onClick={clearFilters} className="text-indigo-600 hover:underline">
            Clear filters
          </button>
        </p>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-4">
        {books.map((book) => (
          <BookCard key={book.id} book={book} />
        ))}
      </div>
    </div>
  )
}
