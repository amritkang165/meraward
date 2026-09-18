import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="mx-auto max-w-md rounded-xl border border-line bg-surface p-6 text-center">
      <h1 className="text-lg font-bold tracking-tight text-ink">Page not found</h1>
      <p className="mt-1 text-sm text-ink-2">That link doesn&rsquo;t lead anywhere in MERAWARD.</p>
      <Link
        to="/ward"
        className="mt-4 inline-block rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-white"
      >
        Find my ward
      </Link>
    </div>
  )
}
