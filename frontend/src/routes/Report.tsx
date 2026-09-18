/**
 * `/report` — photo, one tap, and the complaint drafts itself.
 *
 * Three steps, then a processing screen that polls. The API returns 202 as soon
 * as the complaint is stored; the AI draft happens on a worker, so nobody waits
 * on a model here.
 */
import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ApiError, api, currentPosition, uploadPhoto } from '../api/client'
import type { IssueType } from '../api/types'
import { compressPhoto, formatBytes } from '../lib/image'
import { useDebounced } from '../lib/useDebounced'
import { DemoNotice, ErrorState, Skeleton } from '../components/states'

// MapLibre is by far the heaviest thing we ship. Loading it only when a step
// that needs a map is reached keeps it off the critical path for everything else.
const MapView = lazy(() =>
  import('../components/MapView').then((m) => ({ default: m.MapView })),
)

const ISSUES: { id: IssueType; label: string; blurb: string }[] = [
  { id: 'POTHOLE', label: 'Pothole', blurb: 'Broken road surface' },
  { id: 'STREETLIGHT', label: 'Streetlight', blurb: 'Dark after sunset' },
  { id: 'GARBAGE', label: 'Garbage', blurb: 'Not being collected' },
  { id: 'WATER', label: 'Waterlogging', blurb: 'Drain not clearing' },
  { id: 'OTHER', label: 'Something else', blurb: 'Anything a ward office handles' },
]

const DELHI = { lat: 28.6315, lng: 77.2167 }

type Stage = 'issue' | 'photo' | 'place' | 'sending' | 'done'

export default function Report() {
  const location = useLocation() as { state?: { lat?: number; lng?: number } }
  const [stage, setStage] = useState<Stage>('issue')
  const [issue, setIssue] = useState<IssueType | null>(null)
  const [photo, setPhoto] = useState<{ file: File; preview: string; saved: string } | null>(null)
  const [pin, setPin] = useState(
    location.state?.lat && location.state?.lng
      ? { lat: location.state.lat, lng: location.state.lng }
      : DELHI,
  )
  const [landmark, setLandmark] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [created, setCreated] = useState<{ id: string; token: string } | null>(null)

  // Revoke the object URL when the photo changes or the screen unmounts, so a
  // few retakes don't leak megabytes of blobs on a phone.
  useEffect(() => {
    return () => {
      if (photo) URL.revokeObjectURL(photo.preview)
    }
  }, [photo])

  const debouncedPin = useDebounced(pin, 400)
  const ward = useQuery({
    queryKey: ['ward', debouncedPin.lat.toFixed(5), debouncedPin.lng.toFixed(5)],
    queryFn: () => api.wardByPoint(debouncedPin.lat, debouncedPin.lng),
    enabled: stage === 'place',
    retry: false,
  })

  const onPickPhoto = useCallback(async (file: File | undefined) => {
    if (!file) return
    setError(null)
    setBusy('Preparing photo…')
    try {
      const result = await compressPhoto(file)
      setPhoto({
        file: result.file,
        preview: URL.createObjectURL(result.file),
        saved:
          result.compressedBytes < result.originalBytes
            ? `${formatBytes(result.originalBytes)} → ${formatBytes(result.compressedBytes)}`
            : formatBytes(result.originalBytes),
      })
      setStage('place')
    } catch {
      setError("Couldn't read that photo. Try another one.")
    } finally {
      setBusy(null)
    }
  }, [])

  const submit = useCallback(async () => {
    if (!photo || !issue) return
    setError(null)
    setStage('sending')
    try {
      setBusy('Uploading photo…')
      const presigned = await api.presign(photo.file.type, photo.file.size)
      await uploadPhoto(photo.file, presigned)

      setBusy('Filing the complaint…')
      const result = await api.createComplaint({
        photo_key: presigned.photo_key,
        issue_type: issue,
        lat: pin.lat,
        lng: pin.lng,
        landmark: landmark.trim() || undefined,
      })
      setCreated({ id: result.complaint_id, token: result.status_token })
      setStage('done')
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Something went wrong.')
      setStage('place')
    } finally {
      setBusy(null)
    }
  }, [photo, issue, pin, landmark])

  if (stage === 'done' && created) {
    return <Submitted id={created.id} token={created.token} />
  }

  return (
    <div className="mx-auto max-w-lg space-y-4">
      <Steps stage={stage} />

      {error ? (
        <ErrorState title="That didn't work" message={error} />
      ) : null}

      {stage === 'issue' ? (
        <section>
          <h1 className="text-lg font-bold tracking-tight text-ink">What's the problem?</h1>
          <ul className="mt-3 grid gap-2 sm:grid-cols-2">
            {ISSUES.map((option) => (
              <li key={option.id}>
                <button
                  type="button"
                  onClick={() => {
                    setIssue(option.id)
                    setStage('photo')
                  }}
                  className="w-full rounded-xl border border-line bg-surface p-4 text-left transition-colors hover:border-brand hover:bg-brand-soft/40"
                >
                  <span className="block font-semibold text-ink">{option.label}</span>
                  <span className="mt-0.5 block text-sm text-ink-2">{option.blurb}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {stage === 'photo' ? (
        <section>
          <h1 className="text-lg font-bold tracking-tight text-ink">Take a photo</h1>
          <p className="mt-1 text-sm text-ink-2">
            The photo is the evidence. It's resized on your phone before upload, so it works on
            mobile data.
          </p>
          <label className="mt-4 flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed border-line bg-surface p-8 text-center transition-colors hover:border-brand">
            <span className="text-sm font-semibold text-brand">
              {busy ?? 'Take or choose a photo'}
            </span>
            <span className="text-xs text-ink-3">JPEG, PNG, WebP or HEIC</span>
            <input
              type="file"
              accept="image/*"
              capture="environment"
              className="sr-only"
              onChange={(event) => void onPickPhoto(event.target.files?.[0])}
            />
          </label>
          <button
            type="button"
            onClick={() => setStage('issue')}
            className="mt-3 text-sm font-medium text-ink-3 underline underline-offset-2"
          >
            Back
          </button>
        </section>
      ) : null}

      {(stage === 'place' || stage === 'sending') && photo ? (
        <section className="space-y-4">
          <h1 className="text-lg font-bold tracking-tight text-ink">Where is it?</h1>

          <figure className="overflow-hidden rounded-xl border border-line bg-surface">
            <img
              src={photo.preview}
              alt="The problem you photographed"
              loading="lazy"
              decoding="async"
              className="max-h-56 w-full object-cover"
            />
            <figcaption className="px-3 py-2 text-xs text-ink-3">
              Resized on your phone · {photo.saved}
            </figcaption>
          </figure>

          <Suspense fallback={<Skeleton className="h-56 w-full" />}>
            <MapView
              pin={pin}
              onPinMove={setPin}
              className="h-56 w-full overflow-hidden rounded-xl border border-line"
            />
          </Suspense>

          <button
            type="button"
            onClick={() => void currentPosition().then(setPin).catch(() => {})}
            className="text-sm font-medium text-brand underline underline-offset-2"
          >
            Use my location instead
          </button>

          <div
            className="rounded-xl border border-line bg-surface p-3 text-sm"
            aria-live="polite"
          >
            {ward.isPending ? (
              <Skeleton className="h-5 w-40" />
            ) : ward.isError ? (
              <span className="text-band-moderate">
                {ward.error instanceof ApiError ? ward.error.message : 'Move the pin into Delhi.'}
              </span>
            ) : (
              <>
                <span className="text-ink-3">This goes to </span>
                <span className="font-semibold text-ink">{ward.data.ward_name}</span>
                <span className="font-mono text-xs text-ink-3"> · {ward.data.ward_id}</span>
              </>
            )}
          </div>

          <label className="block">
            <span className="text-[11px] uppercase tracking-wide text-ink-3">
              Nearest landmark (optional)
            </span>
            <input
              type="text"
              value={landmark}
              maxLength={140}
              onChange={(event) => setLandmark(event.target.value)}
              placeholder="e.g. opposite the community park gate"
              className="mt-1 w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-3"
            />
          </label>

          <button
            type="button"
            onClick={() => void submit()}
            disabled={stage === 'sending' || ward.isError || ward.isPending}
            className="w-full rounded-lg bg-brand px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-brand-dark disabled:opacity-60"
          >
            {stage === 'sending' ? (busy ?? 'Sending…') : 'File this complaint'}
          </button>

          <DemoNotice>
            The complaint is drafted in Hindi and English and queued to the ward outbox. On this
            deployment it is delivered to a demo inbox, not to a real official.
          </DemoNotice>
        </section>
      ) : null}
    </div>
  )
}

function Steps({ stage }: { stage: Stage }) {
  const index = stage === 'issue' ? 0 : stage === 'photo' ? 1 : 2
  const labels = ['Problem', 'Photo', 'Place']
  return (
    <ol className="flex gap-1.5" aria-label="Progress">
      {labels.map((label, i) => (
        <li key={label} className="flex-1">
          <div
            className={`h-1 rounded-full ${i <= index ? 'bg-brand' : 'bg-line'}`}
            aria-hidden="true"
          />
          <span className={`mt-1 block text-[11px] ${i <= index ? 'text-brand' : 'text-ink-3'}`}>
            {label}
          </span>
        </li>
      ))}
    </ol>
  )
}

/**
 * The processing screen. Polls until the worker has drafted the letter, then
 * shows it. Polling stops as soon as the draft lands — an interval that runs
 * forever on a backgrounded tab is a battery and billing problem.
 */
function Submitted({ id, token }: { id: string; token: string }) {
  const complaint = useQuery({
    queryKey: ['complaint', id],
    queryFn: () => api.complaint(id),
    refetchInterval: (query) => {
      const status = query.state.data?.draft_status
      return status === 'DRAFTED' || status === 'SENT' || status === 'FAILED' ? false : 2000
    },
    staleTime: 0,
  })

  const drafting = complaint.data?.draft_status === 'PENDING' || complaint.isPending

  // Keep the reporter's own link, so closing the tab doesn't lose it.
  useEffect(() => {
    try {
      localStorage.setItem(`meraward:token:${id}`, token)
    } catch {
      // Private mode or blocked storage. The link on screen still works.
    }
  }, [id, token])

  return (
    <div className="mx-auto max-w-lg space-y-4">
      <div className="rounded-xl border border-line bg-surface p-5 text-center">
        <p className="text-2xl" aria-hidden="true">✓</p>
        <h1 className="mt-1 text-lg font-bold tracking-tight text-ink">Complaint filed</h1>
        <p className="mt-1 font-mono text-xs text-ink-3">{id}</p>
      </div>

      {drafting ? (
        <div className="rounded-xl border border-line bg-surface p-4" aria-live="polite">
          <p className="text-sm font-semibold text-ink">Drafting your complaint…</p>
          <p className="mt-1 text-sm text-ink-2">
            Writing it formally, in Hindi and English, addressed to the right ward office.
          </p>
          <div className="mt-3 space-y-2">
            <Skeleton className="h-4 w-4/5" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/5" />
          </div>
        </div>
      ) : complaint.data ? (
        <BilingualDraft
          subject={complaint.data.subject}
          en={complaint.data.body_en}
          hi={complaint.data.body_hi}
        />
      ) : null}

      <div className="grid gap-2 sm:grid-cols-2">
        <Link
          to={`/c/${id}`}
          className="rounded-lg bg-brand px-4 py-3 text-center text-sm font-semibold text-white"
        >
          Track this complaint
        </Link>
        <Link
          to={`/u/${token}?id=${encodeURIComponent(id)}`}
          className="rounded-lg border border-line bg-surface px-4 py-3 text-center text-sm font-semibold text-ink"
        >
          Your update link
        </Link>
      </div>
      <DemoNotice>
        Keep the update link. It's the only way to mark this complaint acknowledged or resolved —
        there are no accounts here.
      </DemoNotice>
    </div>
  )
}

export function BilingualDraft({
  subject,
  en,
  hi,
}: {
  subject: string | null
  en: string | null
  hi: string | null
}) {
  const [lang, setLang] = useState<'en' | 'hi'>('en')
  const body = useMemo(() => (lang === 'en' ? en : hi), [lang, en, hi])

  if (!en && !hi) return null

  return (
    <article className="rounded-xl border border-line bg-surface">
      <header className="flex items-center gap-2 border-b border-line p-3">
        <h2 className="min-w-0 flex-1 truncate text-sm font-semibold text-ink">
          {subject ?? 'Your complaint'}
        </h2>
        <div className="flex shrink-0 rounded-lg bg-surface-2 p-0.5" role="tablist">
          {(['en', 'hi'] as const).map((code) => (
            <button
              key={code}
              type="button"
              role="tab"
              aria-selected={lang === code}
              onClick={() => setLang(code)}
              className={`rounded-md px-2.5 py-1 text-xs font-semibold transition-colors ${
                lang === code ? 'bg-surface text-ink shadow-sm' : 'text-ink-3'
              }`}
            >
              {code === 'en' ? 'English' : 'हिन्दी'}
            </button>
          ))}
        </div>
      </header>
      <pre className="overflow-x-auto whitespace-pre-wrap p-4 font-sans text-sm leading-relaxed text-ink-2">
        {body}
      </pre>
    </article>
  )
}
