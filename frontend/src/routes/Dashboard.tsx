/**
 * `/dashboard` — every report in Delhi, and which wards are being ignored.
 *
 * Two surfaces: a map (heatmap or points) and the Neglect Index leaderboard.
 * The leaderboard pages rather than rendering ~289 rows at once, and filtering
 * happens against already-fetched data so changing a filter costs no request.
 */
import { lazy, memo, Suspense, useDeferredValue, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { ComplaintStatus, IndexBand, IssueType, LeaderboardRow } from '../api/types'
import { DemoNotice, EmptyState, ErrorState, Skeleton } from '../components/states'

const ComplaintsMap = lazy(() =>
  import('../components/ComplaintsMap').then((m) => ({ default: m.ComplaintsMap })),
)

const PAGE = 25

const STATUSES: (ComplaintStatus | 'ALL')[] = ['ALL', 'OPEN', 'ACKNOWLEDGED', 'RESOLVED']
const ISSUES: (IssueType | 'ALL')[] = ['ALL', 'POTHOLE', 'STREETLIGHT', 'GARBAGE', 'WATER', 'OTHER']

const BAND_CLASS: Record<IndexBand, string> = {
  LOW: 'bg-band-low-soft text-band-low',
  MODERATE: 'bg-band-moderate-soft text-band-moderate',
  HIGH: 'bg-band-high-soft text-band-high',
}

export default function Dashboard() {
  const [status, setStatus] = useState<ComplaintStatus | 'ALL'>('ALL')
  const [issue, setIssue] = useState<IssueType | 'ALL'>('ALL')
  const [heatmap, setHeatmap] = useState(true)
  const [shown, setShown] = useState(PAGE)
  const navigate = useNavigate()

  // One unfiltered fetch, cached; filters are applied client-side. It is a few
  // hundred markers, so refetching per filter change would spend Lambda
  // invocations to do work the browser can do instantly.
  const complaints = useQuery({ queryKey: ['complaints'], queryFn: () => api.complaints() })
  const leaderboard = useQuery({ queryKey: ['leaderboard'], queryFn: () => api.leaderboard() })

  const filtered = useMemo(() => {
    const all = complaints.data?.complaints ?? []
    return all.filter(
      (c) => (status === 'ALL' || c.status === status) && (issue === 'ALL' || c.issue_type === issue),
    )
  }, [complaints.data, status, issue])

  // Keep the map responsive while a filter is being changed rapidly: React can
  // paint the new chips immediately and re-render the heavy map behind them.
  const deferredMarkers = useDeferredValue(filtered)

  const rows = leaderboard.data?.wards ?? []
  const visible = useMemo(() => rows.slice(0, shown), [rows, shown])

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-bold tracking-tight text-ink">Accountability dashboard</h1>
        <p className="mt-1 text-sm text-ink-2">
          Every report, and every ward ranked by how neglected it is. Higher is worse.
        </p>
      </header>

      <section className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <Chips label="Status" options={STATUSES} value={status} onChange={setStatus} />
          <Chips label="Issue" options={ISSUES} value={issue} onChange={setIssue} />
          <button
            type="button"
            onClick={() => setHeatmap((on) => !on)}
            aria-pressed={heatmap}
            className="ml-auto rounded-lg border border-line bg-surface px-3 py-1.5 text-xs font-semibold text-ink"
          >
            {heatmap ? 'Showing heatmap' : 'Showing points'}
          </button>
        </div>

        {complaints.isError ? (
          <ErrorState title="Couldn't load the map" message="Try reloading the page." />
        ) : (
          <Suspense fallback={<Skeleton className="h-[380px] w-full" />}>
            <ComplaintsMap
              markers={deferredMarkers}
              heatmap={heatmap}
              onSelect={(id) => navigate(`/c/${id}`)}
              className="h-[380px] w-full overflow-hidden rounded-xl border border-line"
            />
          </Suspense>
        )}

        <p className="text-xs text-ink-3" aria-live="polite">
          {complaints.isPending
            ? 'Loading reports…'
            : `${filtered.length} report${filtered.length === 1 ? '' : 's'} shown`}
          {complaints.data?.truncated ? ' (capped)' : ''}
        </p>
      </section>

      <section>
        <h2 className="text-[11px] uppercase tracking-wide text-ink-3">Ward Neglect Index</h2>

        {leaderboard.isPending ? (
          <div className="mt-2 space-y-2">
            {Array.from({ length: 6 }, (_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : leaderboard.isError ? (
          <ErrorState title="Couldn't load the leaderboard" message="Try reloading the page." />
        ) : rows.length === 0 ? (
          <EmptyState
            title="No ward has enough reports yet"
            message="A ward needs at least five reports before it gets an index."
          />
        ) : (
          <>
            <ol className="mt-2 divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
              {visible.map((row) => (
                <LeaderRow key={row.ward_id} row={row} />
              ))}
            </ol>

            {shown < rows.length ? (
              <button
                type="button"
                onClick={() => setShown((n) => n + PAGE)}
                className="mt-2 w-full rounded-lg border border-line bg-surface px-4 py-2.5 text-sm font-semibold text-ink"
              >
                Show {Math.min(PAGE, rows.length - shown)} more · {shown} of {rows.length}
              </button>
            ) : null}
          </>
        )}

        {leaderboard.data && leaderboard.data.unranked_count > 0 ? (
          <p className="mt-2 text-xs text-ink-3">
            {leaderboard.data.unranked_count} ward
            {leaderboard.data.unranked_count === 1 ? '' : 's'} have fewer than five reports and are
            not ranked. Too few reports is not the same as being well run.
          </p>
        ) : null}
      </section>

      {leaderboard.data ? <DemoNotice>{leaderboard.data.data_notice}</DemoNotice> : null}
    </div>
  )
}

/**
 * Memoised: changing a map filter re-renders the dashboard, and there is no
 * reason for 25 unchanged leaderboard rows to re-render with it.
 */
const LeaderRow = memo(function LeaderRow({ row }: { row: LeaderboardRow }) {
  return (
    <li>
      <Link
        to={`/ward?ward=${encodeURIComponent(row.ward_id)}`}
        className="flex items-center gap-3 px-3 py-2.5 transition-colors hover:bg-surface-2"
      >
        <span className="w-6 shrink-0 text-right font-mono text-xs tabular-nums text-ink-3">
          {row.rank}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-semibold text-ink">{row.ward_name}</span>
          <span className="block truncate text-xs text-ink-3">
            {row.index_basis.open} open · {row.index_basis.resolved} resolved
          </span>
        </span>
        {row.neglect_index !== null && row.index_band ? (
          <span
            className={`shrink-0 rounded-md px-2 py-1 text-xs font-bold tabular-nums ${BAND_CLASS[row.index_band]}`}
          >
            {row.neglect_index}
          </span>
        ) : (
          <span className="shrink-0 text-xs text-ink-3">—</span>
        )}
      </Link>
    </li>
  )
})

function Chips<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string
  options: T[]
  value: T
  onChange: (next: T) => void
}) {
  return (
    <div className="flex items-center gap-1" role="group" aria-label={label}>
      {options.map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => onChange(option)}
          aria-pressed={value === option}
          className={`rounded-full px-2.5 py-1 text-xs font-semibold transition-colors ${
            value === option
              ? 'bg-brand text-white'
              : 'border border-line bg-surface text-ink-2 hover:bg-surface-2'
          }`}
        >
          {option === 'ALL' ? label : option.charAt(0) + option.slice(1).toLowerCase()}
        </button>
      ))}
    </div>
  )
}
