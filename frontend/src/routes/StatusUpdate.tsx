/**
 * `/u/:token` — the magic link.
 *
 * No login anywhere in this product, so this link *is* the authorisation. The
 * complaint id rides along as a query parameter (`?id=`), because the token on
 * its own identifies permission, not which complaint it belongs to.
 */
import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError, api } from '../api/client'
import type { StatusAction } from '../api/types'
import { ErrorState, LoadingCard } from '../components/states'

const ACTIONS: { id: StatusAction; label: string; blurb: string; tone: string }[] = [
  {
    id: 'acknowledge',
    label: 'Acknowledge',
    blurb: "Someone has seen this and it's being looked at.",
    tone: 'border-line hover:border-band-moderate',
  },
  {
    id: 'resolve',
    label: 'Mark resolved',
    blurb: "It's fixed.",
    tone: 'border-line hover:border-band-low',
  },
  {
    id: 'reopen',
    label: 'Still broken',
    blurb: "It was marked fixed, but it isn't.",
    tone: 'border-line hover:border-band-high',
  },
]

export default function StatusUpdate() {
  const { token = '' } = useParams()
  const [params] = useSearchParams()
  const id = params.get('id') ?? ''
  const queryClient = useQueryClient()
  const [note, setNote] = useState<string | null>(null)

  const complaint = useQuery({
    queryKey: ['complaint', id],
    queryFn: () => api.complaint(id),
    enabled: Boolean(id),
    retry: false,
  })

  const update = useMutation({
    mutationFn: (action: StatusAction) => api.updateStatus(id, token, action),
    onSuccess: (data) => {
      queryClient.setQueryData(['complaint', id], data)
      // The ward index and the dashboard both move when a status changes.
      void queryClient.invalidateQueries({ queryKey: ['leaderboard'] })
      void queryClient.invalidateQueries({ queryKey: ['complaints'] })
      setNote(
        data.changed
          ? `Updated — this complaint is now ${data.status}.`
          : `No change — it was already ${data.status}.`,
      )
    },
    onError: (error) => {
      setNote(error instanceof ApiError ? error.message : 'That did not work.')
    },
  })

  if (!id) {
    return (
      <ErrorState
        title="Incomplete link"
        message="This update link is missing the complaint it belongs to. Use the full link you were given."
      />
    )
  }

  if (complaint.isPending) return <LoadingCard label="Loading complaint" />
  if (complaint.isError) {
    return <ErrorState title="Couldn't load that complaint" message="Check the link and try again." />
  }

  const current = complaint.data

  return (
    <div className="mx-auto max-w-lg space-y-4">
      <header>
        <h1 className="text-lg font-bold tracking-tight text-ink">Update this complaint</h1>
        <p className="mt-1 text-sm text-ink-2">
          {current.issue_type.charAt(0) + current.issue_type.slice(1).toLowerCase()} in{' '}
          {current.ward_name} · currently <strong className="text-ink">{current.status}</strong>
        </p>
      </header>

      {note ? (
        <p
          className="rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink"
          role="status"
          aria-live="polite"
        >
          {note}
        </p>
      ) : null}

      <ul className="space-y-2">
        {ACTIONS.map((action) => (
          <li key={action.id}>
            <button
              type="button"
              disabled={update.isPending}
              onClick={() => update.mutate(action.id)}
              className={`w-full rounded-xl border bg-surface p-4 text-left transition-colors disabled:opacity-60 ${action.tone}`}
            >
              <span className="block font-semibold text-ink">{action.label}</span>
              <span className="mt-0.5 block text-sm text-ink-2">{action.blurb}</span>
            </button>
          </li>
        ))}
      </ul>

      <Link
        to={`/c/${id}`}
        className="block rounded-lg border border-line bg-surface px-4 py-2.5 text-center text-sm font-semibold text-ink"
      >
        View the full complaint
      </Link>

      <p className="text-xs leading-relaxed text-ink-3">
        Anyone with this link can change the status, and there are no accounts here. Reopening a
        complaint keeps its history — a resolution that did not hold stays on the record.
      </p>
    </div>
  )
}
