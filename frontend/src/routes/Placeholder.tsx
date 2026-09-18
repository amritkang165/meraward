import { Link } from 'react-router-dom'

/**
 * An honest stub.
 *
 * Says plainly that the screen is not built yet and what it will do, rather
 * than showing a broken or empty version of it. Better to be clear about the
 * state of the build than to fake a screen.
 */
export function Placeholder({
  title,
  blurb,
  next,
}: {
  title: string
  blurb: string
  next: string[]
}) {
  return (
    <div className="mx-auto max-w-lg rounded-xl border border-dashed border-line bg-surface p-6">
      <h1 className="text-lg font-bold tracking-tight text-ink">{title}</h1>
      <p className="mt-1 text-sm text-ink-2">{blurb}</p>
      {next.length > 0 ? (
        <>
          <p className="mt-4 text-[11px] uppercase tracking-wide text-ink-3">Being built</p>
          <ul className="mt-1.5 space-y-1 text-sm text-ink-2">
            {next.map((item) => (
              <li key={item} className="flex gap-2">
                <span aria-hidden="true" className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-line" />
                {item}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      <Link
        to="/ward"
        className="mt-5 inline-block rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-white"
      >
        Find my ward
      </Link>
    </div>
  )
}
