import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { Icon, type IconName } from '../components/Icon'
import { Skeleton } from '../components/states'

const METHODS: Array<{
  mode: 'voice' | 'photo' | 'write'
  icon: IconName
  eyebrow: string
  title: string
  description: string
  cta: string
  tone: string
}> = [
  { mode: 'voice', icon: 'microphone', eyebrow: 'Fastest', title: 'Speak your issue', description: 'Talk naturally. Review the transcript before anything is filed.', cta: 'Start speaking', tone: 'method-voice' },
  { mode: 'photo', icon: 'camera', eyebrow: 'Visual evidence', title: 'Report with a photo', description: 'Take or upload a photo, choose the issue, and pin the exact place.', cta: 'Add a photo', tone: 'method-photo' },
  { mode: 'write', icon: 'write', eyebrow: 'More detail', title: 'Write it yourself', description: 'Describe what happened in your own words and add evidence if you have it.', cta: 'Write a complaint', tone: 'method-write' },
]

const PROCESS = [
  ['Tell us', 'Speak, upload a photo, or write in your own words.'],
  ['Review it', 'Check the issue, ward, evidence, and complaint language.'],
  ['Track it', 'Get a permanent ID and follow every status change publicly.'],
]

export default function Home() {
  const navigate = useNavigate()
  const [trackingId, setTrackingId] = useState('')
  const complaints = useQuery({ queryKey: ['complaints', 'home-summary'], queryFn: () => api.complaints(), staleTime: 60_000 })
  const rows = complaints.data?.complaints ?? []
  const resolved = rows.filter((row) => row.status === 'RESOLVED').length
  const active = rows.filter((row) => row.status !== 'RESOLVED').length

  function trackComplaint() {
    const id = trackingId.trim()
    if (id) navigate(`/c/${encodeURIComponent(id)}`)
  }

  return (
    <div className="space-y-7 pb-5">
      <section className="hero-panel overflow-hidden rounded-[1.75rem] border border-white/60 px-5 py-7 shadow-[0_24px_80px_rgba(8,47,73,0.12)] sm:px-8 sm:py-10">
        <div className="relative z-10 grid items-center gap-8 lg:grid-cols-[1.15fr_.85fr]">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-brand/10 bg-white/70 px-3 py-1.5 text-xs font-bold text-brand-dark shadow-sm backdrop-blur">
              <Icon name="sparkles" className="h-4 w-4" /> AI-assisted civic reporting · Delhi demo
            </div>
            <h1 className="mt-5 max-w-3xl text-balance text-[2.35rem] font-black leading-[1.02] tracking-[-0.045em] text-ink sm:text-5xl">
              A civic complaint that feels less like a form.
            </h1>
            <p className="mt-4 max-w-2xl text-pretty text-base leading-7 text-ink-2 sm:text-lg">
              Tell us what happened. MERAWARD finds the ward, prepares a formal bilingual complaint, and gives you a public trail to follow.
            </p>
            <div className="mt-6 flex flex-wrap gap-2.5">
              <Link to="/report?mode=voice" className="button-primary inline-flex items-center gap-2">Report an issue <Icon name="arrow" className="h-4 w-4" /></Link>
              <Link to="/dashboard" className="button-secondary inline-flex items-center gap-2">View public dashboard</Link>
            </div>
            <div className="mt-7 flex flex-wrap gap-x-5 gap-y-2 text-xs font-semibold text-ink-2">
              <span className="inline-flex items-center gap-1.5"><Icon name="shield" className="h-4 w-4 text-brand" /> No signup</span>
              <span className="inline-flex items-center gap-1.5"><Icon name="globe" className="h-4 w-4 text-brand" /> English + हिन्दी</span>
              <span className="inline-flex items-center gap-1.5"><Icon name="map" className="h-4 w-4 text-brand" /> Ward-aware routing</span>
            </div>
          </div>
          <div className="hero-orbit" aria-hidden="true">
            <div className="hero-orbit__ring" />
            <div className="hero-orbit__core"><Icon name="location" className="h-8 w-8" /><strong>Delhi</strong><span>289 mapped wards</span></div>
            <span className="hero-orbit__chip hero-orbit__chip--one">Speak</span>
            <span className="hero-orbit__chip hero-orbit__chip--two">Review</span>
            <span className="hero-orbit__chip hero-orbit__chip--three">Track</span>
          </div>
        </div>
      </section>

      <section aria-labelledby="report-method-heading">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div><p className="section-kicker">Start a report</p><h2 id="report-method-heading" className="mt-1 text-2xl font-extrabold tracking-tight text-ink">How would you like to tell us?</h2></div>
          <p className="max-w-sm text-sm text-ink-3">All three paths meet at the same review screen before submission.</p>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {METHODS.map((method) => (
            <Link key={method.mode} to={`/report?mode=${method.mode}`} className={`method-card ${method.tone} group`}>
              <div className="flex items-start justify-between gap-3">
                <span className="method-icon"><Icon name={method.icon} className="h-7 w-7" /></span>
                <span className="rounded-full bg-white/70 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.12em] text-ink-3">{method.eyebrow}</span>
              </div>
              <h3 className="mt-5 text-lg font-extrabold tracking-tight text-ink">{method.title}</h3>
              <p className="mt-1.5 min-h-12 text-sm leading-6 text-ink-2">{method.description}</p>
              <span className="mt-5 inline-flex items-center gap-2 text-sm font-bold text-current">{method.cta} <Icon name="arrow" className="h-4 w-4 transition-transform group-hover:translate-x-1" /></span>
            </Link>
          ))}
        </div>
      </section>

      <section className="grid gap-3 lg:grid-cols-[1.1fr_.9fr]">
        <div className="app-card p-5 sm:p-6">
          <div className="flex items-center gap-2"><span className="icon-badge"><Icon name="document" className="h-5 w-5" /></span><div><p className="section-kicker">Already reported?</p><h2 className="font-bold text-ink">Track a complaint</h2></div></div>
          <form className="mt-4 flex flex-col gap-2 sm:flex-row" onSubmit={(event) => { event.preventDefault(); trackComplaint() }}>
            <label className="sr-only" htmlFor="complaint-id">Complaint ID</label>
            <input id="complaint-id" value={trackingId} onChange={(event) => setTrackingId(event.target.value)} placeholder="Paste your complaint ID" className="min-h-12 flex-1 rounded-xl border border-line bg-ground/70 px-4 text-sm text-ink placeholder:text-ink-3" />
            <button type="submit" disabled={!trackingId.trim()} className="button-primary disabled:cursor-not-allowed disabled:opacity-50">Track status</button>
          </form>
        </div>
        <div className="app-card grid grid-cols-3 divide-x divide-line overflow-hidden p-2">
          <Stat value={rows.length} label="Reports" loading={complaints.isPending} />
          <Stat value={active} label="Active" loading={complaints.isPending} />
          <Stat value={resolved} label="Resolved" loading={complaints.isPending} />
        </div>
      </section>

      <section className="app-card p-5 sm:p-7">
        <div className="grid gap-6 lg:grid-cols-[.55fr_1.45fr] lg:items-center">
          <div><p className="section-kicker">Human in the loop</p><h2 className="mt-1 text-2xl font-extrabold tracking-tight text-ink">You stay in control.</h2><p className="mt-2 text-sm leading-6 text-ink-2">AI helps structure the complaint. It never submits behind your back.</p></div>
          <ol className="grid gap-3 sm:grid-cols-3">
            {PROCESS.map(([title, description], index) => (
              <li key={title} className="rounded-2xl bg-ground/80 p-4"><span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-ink text-xs font-black text-white">{index + 1}</span><h3 className="mt-3 font-bold text-ink">{title}</h3><p className="mt-1 text-sm leading-5 text-ink-3">{description}</p></li>
            ))}
          </ol>
        </div>
      </section>
    </div>
  )
}

function Stat({ value, label, loading }: { value: number; label: string; loading: boolean }) {
  return <div className="flex min-h-28 flex-col items-center justify-center px-2 text-center">{loading ? <Skeleton className="h-8 w-12" /> : <strong className="text-2xl font-black tabular-nums text-ink">{value}</strong>}<span className="mt-1 text-xs font-semibold text-ink-3">{label}</span></div>
}
