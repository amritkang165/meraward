/**
 * `/c/:id` — the shareable record of one report.
 *
 * This is the artifact people send each other, so it has to stand alone: the
 * photo, the letter in both languages, where it is, and what has happened to it.
 */
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ApiError, api } from '../api/client'
import { DemoNotice, ErrorState, LoadingCard } from '../components/states'
import { BilingualDraft } from './Report'

const STATUS_CLASS: Record<string, string> = {
  OPEN: 'bg-band-high-soft text-band-high',
  ACKNOWLEDGED: 'bg-band-moderate-soft text-band-moderate',
  RESOLVED: 'bg-band-low-soft text-band-low',
}

export default function ComplaintDetail() {
  const { id = '' } = useParams()
  const complaint = useQuery({
    queryKey: ['complaint', id],
    queryFn: () => api.complaint(id),
    enabled: Boolean(id),
    retry: false,
    // Keep polling only while the draft is still being written.
    refetchInterval: (query) =>
      query.state.data?.draft_status === 'PENDING' ? 3000 : false,
  })

  if (complaint.isPending) return <LoadingCard label="Loading complaint" />

  if (complaint.isError) {
    const notFound = complaint.error instanceof ApiError && complaint.error.status === 404
    return (
      <ErrorState
        title={notFound ? 'No such complaint' : "Couldn't load that"}
        message={
          notFound
            ? "That complaint id doesn't exist. Check the link."
            : 'Something went wrong. Try reloading.'
        }
      />
    )
  }

  const c = complaint.data

  return (
    <article className="mx-auto max-w-2xl space-y-4">
      <header className="flex flex-wrap items-start gap-3">
        <div className="min-w-0 flex-1">
          <p className="font-mono text-xs text-ink-3">{c.complaint_id}</p>
          <h1 className="text-lg font-bold tracking-tight text-ink">
            {c.issue_type.charAt(0) + c.issue_type.slice(1).toLowerCase()} in {c.ward_name}
          </h1>
          {c.landmark ? <p className="text-sm text-ink-2">Near {c.landmark}</p> : null}
        </div>
        <span
          className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-bold ${STATUS_CLASS[c.status] ?? ''}`}
        >
          {c.status}
        </span>
      </header>

      {c.is_demo ? (
        <p className="rounded-lg bg-surface-2 px-3 py-2 text-xs font-semibold text-ink-3">
          This is a demonstration record, not a real report.
        </p>
      ) : null}

      {c.photo_url ? (
        <img
          src={c.photo_url}
          alt={`Reported ${c.issue_type.toLowerCase()} in ${c.ward_name}`}
          loading="lazy"
          decoding="async"
          className="w-full rounded-xl border border-line bg-surface-2 object-cover"
        />
      ) : null}

      <BilingualDraft subject={c.subject} en={c.body_en} hi={c.body_hi} />

      <section className="rounded-xl border border-line bg-surface p-4">
        <h2 className="text-[11px] uppercase tracking-wide text-ink-3">What's happened</h2>
        <ol className="mt-2 space-y-3">
          {c.timeline.map((step, i) => (
            <li key={`${step.status}-${step.at}-${i}`} className="flex gap-3">
              <span
                aria-hidden="true"
                className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-brand"
              />
              <span className="min-w-0">
                <span className="block text-sm font-medium text-ink">{step.label}</span>
                <time className="block text-xs text-ink-3" dateTime={step.at}>
                  {new Date(step.at).toLocaleString('en-IN', {
                    dateStyle: 'medium',
                    timeStyle: 'short',
                  })}
                </time>
              </span>
            </li>
          ))}
        </ol>
      </section>

      <section className="rounded-xl border border-line bg-surface p-4 text-sm">
        <h2 className="text-[11px] uppercase tracking-wide text-ink-3">Ward</h2>
        <p className="mt-1 font-semibold text-ink">{c.ward?.ward_name ?? c.ward_name}</p>
        <p className="font-mono text-xs text-ink-3">{c.ward_id}</p>
        {c.ward?.zone ? <p className="text-ink-2">{c.ward.zone}</p> : null}
      </section>

      <DemoNotice>
        Delivery on this deployment goes to a demo inbox, never to a real official.
      </DemoNotice>
    </article>
  )
}
