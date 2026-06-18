import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center text-center">
      <h1 className="text-2xl font-semibold text-gray-900">Page not found</h1>
      <p className="mt-2 text-gray-500">The page you&apos;re looking for doesn&apos;t exist.</p>
      <Link to="/" className="mt-4 text-indigo-600 hover:underline">
        Back to home
      </Link>
    </div>
  )
}
