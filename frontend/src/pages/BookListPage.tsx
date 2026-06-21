import { useEffect, useState } from 'react'
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

const PAGE_SIZE = 50

export function BookListPage() {
  const { user } = useAuth()
  const canEdit = !!user && roleAtLeast(user.role, 'librarian')

  const [q, setQ] = useState('')
  const [categoryId, setCategoryId] = useState<number | null>(null)
  const [editionId, setEditionId] = useState<number | null>(null)
  const [page, setPage] = useState(0)
  const debouncedQ = useDebouncedValue(q, 300)

  const hasActiveFilters = debouncedQ.trim() !== '' || categoryId !== null || editionId !== null

  // Changing the search/filters makes the current page number meaningless --
  // jump back to the first page rather than risk landing on an empty one.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    setPage(0)
  }, [debouncedQ, categoryId, editionId])
  /* eslint-enable react-hooks/set-state-in-effect */

  const { data: categories = [] } = useQuery({ queryKey: ['categories'], queryFn: listCategories })
  const { data: editions = [] } = useQuery({ queryKey: ['editions'], queryFn: listEditions })

  const {
    data: rawBooks = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['books', { q: debouncedQ, categoryId, editionId, page }],
    queryFn: () =>
      listBooks({
        q: debouncedQ.trim() || undefined,
        category_id: categoryId ?? undefined,
        edition_id: editionId ?? undefined,
        // Ask for one extra book -- if it comes back, there's a next page.
        // Avoids needing a separate total-count endpoint just for paging.
        limit: PAGE_SIZE + 1,
        offset: page * PAGE_SIZE,
      }),
  })

  const hasNextPage = rawBooks.length > PAGE_SIZE
  const books = rawBooks.slice(0, PAGE_SIZE)

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

      {(page > 0 || hasNextPage) && (
        <div className="mt-4 flex items-center justify-center gap-4">
          <button
            type="button"
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-40"
          >
            Previous
          </button>
          <span className="text-sm text-gray-500">Page {page + 1}</span>
          <button
            type="button"
            disabled={!hasNextPage}
            onClick={() => setPage((p) => p + 1)}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
