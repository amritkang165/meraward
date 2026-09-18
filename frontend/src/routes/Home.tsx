import { Link } from 'react-router-dom'

const STEPS = [
  { n: 1, t: 'Find your ward', d: 'Drop a pin or use your location. You get the ward, its zone, and how neglected it is.' },
  { n: 2, t: 'Report in one tap', d: 'A photo and an issue type. The complaint drafts itself in Hindi and English, addressed to the right ward office.' },
  { n: 3, t: 'Watch it publicly', d: 'Every report is tracked in the open, from reported to acknowledged to resolved.' },
]

export default function Home() {
  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-line bg-surface px-5 py-8 sm:px-8 sm:py-10">
        <p className="text-xs font-semibold uppercase tracking-wider text-brand">Delhi civic accountability</p>
        <h1 className="mt-2 max-w-2xl text-balance text-2xl font-bold leading-tight tracking-tight text-ink sm:text-3xl">
          Know your ward. Route your complaint. See who&rsquo;s ignoring you.
        </h1>
        <p className="mt-3 max-w-xl text-sm leading-relaxed text-ink-2">
          Potholes, streetlights, garbage and drains are a ward councillor&rsquo;s job. Almost nobody
          knows which ward they live in, complaints disappear into portals, and there is no public
          record of which areas get ignored. This fixes the first part, and measures the rest.
        </p>
        <div className="mt-5 flex flex-wrap gap-2">
          <Link to="/ward" className="rounded-lg bg-brand px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-dark">
            Find my ward
          </Link>
          <Link to="/dashboard" className="rounded-lg border border-line bg-surface px-5 py-2.5 text-sm font-semibold text-ink transition-colors hover:bg-surface-2">
            See the dashboard
          </Link>
        </div>
      </section>

      <section>
        <h2 className="text-[11px] uppercase tracking-wide text-ink-3">How it works</h2>
        <ol className="mt-3 grid gap-3 sm:grid-cols-3">
          {STEPS.map((s) => (
            <li key={s.n} className="rounded-xl border border-line bg-surface p-4">
              <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-brand-soft text-xs font-bold text-brand-dark">
                {s.n}
              </span>
              <h3 className="mt-2.5 font-semibold text-ink">{s.t}</h3>
              <p className="mt-1 text-sm leading-relaxed text-ink-2">{s.d}</p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  )
}
