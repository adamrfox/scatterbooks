import { Link } from 'react-router-dom'
import { bookImageThumbUrl } from '../api/images'
import type { Book } from '../types'

export function BookCard({ book }: { book: Book }) {
  return (
    <Link
      to={`/books/${book.id}`}
      className="flex gap-3 rounded-lg border border-gray-200 bg-white p-3 shadow-sm hover:shadow md:flex-col md:gap-2"
    >
      <div className="h-20 w-16 flex-shrink-0 overflow-hidden rounded-md bg-gray-100 md:h-40 md:w-full">
        {book.cover_image_id ? (
          <img
            src={bookImageThumbUrl(book.id, book.cover_image_id)}
            alt=""
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-gray-300">
            <BookPlaceholderIcon />
          </div>
        )}
      </div>
      <div className="flex flex-col justify-center md:justify-start">
        <span className="font-medium text-gray-900">{book.title}</span>
        <span className="text-sm text-gray-500">{book.author}</span>
        {book.category && (
          <span className="mt-1 inline-block w-fit rounded-full bg-indigo-50 px-2 py-0.5 text-xs text-indigo-700">
            {book.category.name}
          </span>
        )}
      </div>
    </Link>
  )
}

function BookPlaceholderIcon() {
  return (
    <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25"
      />
    </svg>
  )
}
