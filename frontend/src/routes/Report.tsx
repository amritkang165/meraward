import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ApiError, api, currentPosition, uploadPhoto } from '../api/client'
import type { IssueType } from '../api/types'
import { compressPhoto, formatBytes } from '../lib/image'
import { useDebounced } from '../lib/useDebounced'
import { DemoNotice, ErrorState, Skeleton, Spinner } from '../components/states'
import { Icon, type IconName } from '../components/Icon'
import { useGuest } from '../auth/GuestAuth'

const MapView = lazy(() => import('../components/MapView').then((module) => ({ default: module.MapView })))

const ISSUES: Array<{ id: IssueType; label: string; blurb: string }> = [
  { id: 'POTHOLE', label: 'Pothole', blurb: 'Broken or unsafe road surface' },
  { id: 'STREETLIGHT', label: 'Streetlight', blurb: 'Dark or unsafe after sunset' },
  { id: 'GARBAGE', label: 'Garbage', blurb: 'Waste is not being collected' },
  { id: 'WATER', label: 'Waterlogging', blurb: 'Standing water or blocked drain' },
  { id: 'OTHER', label: 'Something else', blurb: 'Another ward-level civic issue' },
]

const METHODS: Record<EntryMode, { title: string; short: string; icon: IconName }> = {
  voice: { title: 'Tell us what happened', short: 'Voice', icon: 'microphone' },
  photo: { title: 'Report using a photo', short: 'Photo', icon: 'camera' },
  write: { title: 'Describe the issue', short: 'Write', icon: 'write' },
}

const DELHI = { lat: 28.6315, lng: 77.2167 }
type EntryMode = 'voice' | 'photo' | 'write'
type Stage = 'input' | 'details' | 'place' | 'review' | 'sending' | 'done'
type PhotoState = { file: File; preview: string; saved: string }

interface SpeechResultEvent {
  results: ArrayLike<{ 0: { transcript: string }; isFinal: boolean }>
}

interface SpeechRecognitionLike {
  lang: string
  continuous: boolean
  interimResults: boolean
  onresult: ((event: SpeechResultEvent) => void) | null
  onerror: (() => void) | null
  onend: (() => void) | null
  start(): void
  stop(): void
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike

export default function Report() {
  const { profile, rememberComplaint } = useGuest()
  const [searchParams, setSearchParams] = useSearchParams()
  const location = useLocation() as { state?: { lat?: number; lng?: number } }
  const requestedMode = searchParams.get('mode')
  const initialMode: EntryMode | null = requestedMode === 'voice' || requestedMode === 'photo' || requestedMode === 'write' ? requestedMode : null
  const [mode, setMode] = useState<EntryMode | null>(initialMode)
  const [stage, setStage] = useState<Stage>('input')
  const [issue, setIssue] = useState<IssueType | null>(null)
  const [description, setDescription] = useState('')
  const [photo, setPhoto] = useState<PhotoState | null>(null)
  const [pin, setPin] = useState(location.state?.lat && location.state?.lng ? { lat: location.state.lat, lng: location.state.lng } : DELHI)
  const [landmark, setLandmark] = useState('')
  const [language, setLanguage] = useState<'en' | 'hi'>('en')
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [recording, setRecording] = useState(false)
  const [locating, setLocating] = useState(false)
  const [created, setCreated] = useState<{ id: string; token: string } | null>(null)
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)

  useEffect(() => () => {
    recognitionRef.current?.stop()
    if (photo) URL.revokeObjectURL(photo.preview)
  }, [photo])

  const debouncedPin = useDebounced(pin, 400)
  const ward = useQuery({
    queryKey: ['ward', debouncedPin.lat.toFixed(5), debouncedPin.lng.toFixed(5)],
    queryFn: () => api.wardByPoint(debouncedPin.lat, debouncedPin.lng),
    enabled: stage === 'place' || stage === 'review' || stage === 'sending',
    retry: false,
  })

  const selectMode = useCallback((next: EntryMode) => {
    setMode(next)
    setStage('input')
    setSearchParams({ mode: next }, { replace: true })
    setError(null)
  }, [setSearchParams])

  const onPickPhoto = useCallback(async (file: File | undefined) => {
    if (!file) return
    setError(null)
    setBusy('Preparing photo…')
    try {
      const result = await compressPhoto(file)
      setPhoto((current) => {
        if (current) URL.revokeObjectURL(current.preview)
        return {
          file: result.file,
          preview: URL.createObjectURL(result.file),
          saved: result.compressedBytes < result.originalBytes
            ? `${formatBytes(result.originalBytes)} → ${formatBytes(result.compressedBytes)}`
            : formatBytes(result.originalBytes),
        }
      })
      if (mode === 'photo' && stage === 'input') setStage('details')
    } catch {
      setError("Couldn't read that photo. Try another one.")
    } finally {
      setBusy(null)
    }
  }, [mode, stage])

  const startVoice = useCallback(() => {
    const browserWindow = window as typeof window & {
      SpeechRecognition?: SpeechRecognitionConstructor
      webkitSpeechRecognition?: SpeechRecognitionConstructor
    }
    const Recognition = browserWindow.SpeechRecognition ?? browserWindow.webkitSpeechRecognition
    if (!Recognition) {
      setError('Voice capture is not supported in this browser. You can type the transcript below instead.')
      return
    }
    setError(null)
    const recognition = new Recognition()
    recognition.lang = language === 'hi' ? 'hi-IN' : 'en-IN'
    recognition.continuous = true
    recognition.interimResults = true
    recognition.onresult = (event) => {
      let next = ''
      for (let index = 0; index < event.results.length; index += 1) next += event.results[index][0].transcript
      if (next.trim()) setDescription(next.trim())
    }
    recognition.onerror = () => {
      setRecording(false)
      setError("We couldn't hear that clearly. Try again or type what happened.")
    }
    recognition.onend = () => setRecording(false)
    recognitionRef.current = recognition
    recognition.start()
    setRecording(true)
  }, [language])

  const stopVoice = useCallback(() => {
    recognitionRef.current?.stop()
    setRecording(false)
  }, [])

  const continueFromInput = useCallback(() => {
    if (!mode) return
    if ((mode === 'voice' || mode === 'write') && description.trim().length < 8) {
      setError('Add a little more detail so we can prepare a useful complaint.')
      return
    }
    if (!issue && description) setIssue(guessIssue(description))
    setError(null)
    setStage('details')
  }, [mode, description, issue])

  const submit = useCallback(async () => {
    if (!issue || !mode || !ward.data) return
    setError(null)
    setStage('sending')
    try {
      let photoKey: string | undefined
      if (photo) {
        setBusy('Uploading evidence…')
        const presigned = await api.presign(photo.file.type, photo.file.size)
        await uploadPhoto(photo.file, presigned)
        photoKey = presigned.photo_key
      }
      setBusy('Creating your complaint…')
      const result = await api.createComplaint({
        photo_key: photoKey,
        issue_type: issue,
        lat: pin.lat,
        lng: pin.lng,
        landmark: landmark.trim() || undefined,
        description: description.trim() || undefined,
        input_mode: mode,
        preferred_language: language,
      })
      rememberComplaint(result.complaint_id)
      setCreated({ id: result.complaint_id, token: result.status_token })
      setStage('done')
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Something went wrong.')
      setStage('review')
    } finally {
      setBusy(null)
    }
  }, [description, issue, language, landmark, mode, photo, pin, rememberComplaint, ward.data])

  const useMyLocation = useCallback(async () => {
    setLocating(true)
    setError(null)
    try {
      setPin(await currentPosition())
    } catch {
      setError('Location is unavailable. Move the pin on the map instead.')
    } finally {
      setLocating(false)
    }
  }, [])

  if (stage === 'done' && created) return <Submitted id={created.id} token={created.token} />
  if (!mode) return <ModeChooser onSelect={selectMode} />

  return (
    <div className="mx-auto max-w-3xl space-y-5 pb-8">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <button type="button" onClick={() => { setMode(null); setSearchParams({}, { replace: true }); setStage('input') }} className="text-xs font-bold text-brand">← Change method</button>
          <h1 className="mt-2 text-2xl font-black tracking-tight text-ink">{METHODS[mode].title}</h1>
          <p className="mt-1 text-sm text-ink-2">Nothing is submitted until you review and confirm it.</p>
        </div>
        <span className="inline-flex items-center gap-2 rounded-full bg-brand-soft px-3 py-1.5 text-xs font-bold text-brand-dark"><Icon name={METHODS[mode].icon} className="h-4 w-4" /> {METHODS[mode].short} report</span>
      </header>

      <Progress stage={stage} />
      {error ? <ErrorState title="Let's fix that" message={error} /> : null}

      {stage === 'input' ? (
        <section className="app-card p-5 sm:p-7">
          {mode === 'voice' ? (
            <VoiceInput description={description} recording={recording} language={language} onDescription={setDescription} onLanguage={setLanguage} onStart={startVoice} onStop={stopVoice} />
          ) : mode === 'photo' ? (
            <PhotoPicker photo={photo} busy={busy} onPick={onPickPhoto} prominent />
          ) : (
            <TextInput value={description} onChange={setDescription} />
          )}
          {mode !== 'photo' ? <button type="button" onClick={continueFromInput} className="button-primary mt-5 inline-flex w-full items-center gap-2 sm:w-auto">Continue <Icon name="arrow" className="h-4 w-4" /></button> : null}
        </section>
      ) : null}

      {stage === 'details' ? (
        <section className="app-card space-y-6 p-5 sm:p-7">
          <div><p className="section-kicker">Confirm the issue</p><h2 className="mt-1 text-xl font-extrabold text-ink">What should the ward office know?</h2></div>
          <IssuePicker value={issue} onChange={setIssue} />
          {mode === 'photo' ? <TextInput value={description} onChange={setDescription} optional /> : null}
          {mode !== 'photo' ? <PhotoPicker photo={photo} busy={busy} onPick={onPickPhoto} /> : null}
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-between">
            <button type="button" onClick={() => setStage('input')} className="button-secondary">Back</button>
            <button type="button" disabled={!issue || (!photo && description.trim().length < 8)} onClick={() => setStage('place')} className="button-primary inline-flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-50">Confirm details <Icon name="arrow" className="h-4 w-4" /></button>
          </div>
        </section>
      ) : null}

      {stage === 'place' ? (
        <section className="app-card space-y-4 p-5 sm:p-7">
          <div><p className="section-kicker">Route it correctly</p><h2 className="mt-1 text-xl font-extrabold text-ink">Where is the problem?</h2><p className="mt-1 text-sm text-ink-2">Move the pin or use your current location. You can review the ward before filing.</p></div>
          <Suspense fallback={<Skeleton className="h-64 w-full" />}><MapView pin={pin} onPinMove={setPin} className="h-64 w-full overflow-hidden rounded-2xl border border-line sm:h-80" /></Suspense>
          <div className="grid gap-3 sm:grid-cols-[auto_1fr]">
            <button type="button" disabled={locating} onClick={() => void useMyLocation()} className="button-secondary inline-flex items-center gap-2 disabled:opacity-60">{locating ? <Spinner /> : <Icon name="location" className="h-4 w-4 text-brand" />} {locating ? 'Finding you…' : 'Use my location'}</button>
            <div className="rounded-xl border border-line bg-ground/70 px-4 py-3 text-sm" aria-live="polite">
              {ward.isPending ? <Skeleton className="h-5 w-44" /> : ward.isError ? <span className="text-band-moderate">Move the pin inside Delhi.</span> : <span><span className="text-ink-3">Selected ward </span><strong className="text-ink">{ward.data.ward_name}</strong><span className="ml-1 font-mono text-xs text-ink-3">{ward.data.ward_id}</span></span>}
            </div>
          </div>
          <label className="block"><span className="text-xs font-bold text-ink-2">Nearest landmark <span className="font-normal text-ink-3">(optional)</span></span><input value={landmark} maxLength={140} onChange={(event) => setLandmark(event.target.value)} placeholder="e.g. opposite the community park gate" className="mt-1.5 min-h-12 w-full rounded-xl border border-line bg-white px-4 text-sm text-ink placeholder:text-ink-3" /></label>
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-between"><button type="button" onClick={() => setStage('details')} className="button-secondary">Back</button><button type="button" disabled={ward.isPending || ward.isError} onClick={() => setStage('review')} className="button-primary inline-flex items-center gap-2 disabled:opacity-50">Review complaint <Icon name="arrow" className="h-4 w-4" /></button></div>
        </section>
      ) : null}

      {(stage === 'review' || stage === 'sending') && issue && ward.data ? (
        <ReviewComplaint mode={mode} issue={issue} description={description} photo={photo} landmark={landmark} wardName={ward.data.ward_name} wardId={ward.data.ward_id} language={language} busy={busy} sending={stage === 'sending'} guestAlias={profile?.alias ?? null} onLanguage={setLanguage} onEdit={(target) => setStage(target)} onSubmit={() => void submit()} />
      ) : null}
    </div>
  )
}

function ModeChooser({ onSelect }: { onSelect: (mode: EntryMode) => void }) {
  return (
    <section className="mx-auto max-w-3xl py-4 text-center">
      <p className="section-kicker">New complaint</p><h1 className="mt-2 text-3xl font-black tracking-tight text-ink">How would you like to tell us?</h1><p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-ink-2">Choose the easiest way. You will review everything before it is submitted.</p>
      <div className="mt-6 grid gap-3 sm:grid-cols-3">{(Object.keys(METHODS) as EntryMode[]).map((item) => <button key={item} type="button" onClick={() => onSelect(item)} className="app-card flex min-h-44 flex-col items-center justify-center p-5 text-center transition-transform hover:-translate-y-1"><span className="icon-badge"><Icon name={METHODS[item].icon} className="h-5 w-5" /></span><strong className="mt-3 text-ink">{METHODS[item].short}</strong><span className="mt-1 text-xs text-ink-3">{METHODS[item].title}</span></button>)}</div>
    </section>
  )
}

function VoiceInput({ description, recording, language, onDescription, onLanguage, onStart, onStop }: { description: string; recording: boolean; language: 'en' | 'hi'; onDescription: (value: string) => void; onLanguage: (value: 'en' | 'hi') => void; onStart: () => void; onStop: () => void }) {
  return <div className="text-center"><div className={`mx-auto flex h-28 w-28 items-center justify-center rounded-full ${recording ? 'voice-recording bg-band-high-soft text-band-high' : 'bg-brand-soft text-brand-dark'}`}><Icon name="microphone" className="h-11 w-11" /></div><h2 className="mt-4 text-xl font-extrabold text-ink">{recording ? 'Listening…' : 'Speak naturally'}</h2><p className="mx-auto mt-1 max-w-md text-sm leading-6 text-ink-2">Try: “There is a large pothole near the school and it is dangerous after dark.”</p><div className="mt-4 flex justify-center gap-2"><button type="button" onClick={recording ? onStop : onStart} className={recording ? 'button-secondary' : 'button-primary'}>{recording ? 'Stop listening' : 'Start speaking'}</button><select value={language} onChange={(event) => onLanguage(event.target.value as 'en' | 'hi')} aria-label="Speech language" className="min-h-12 rounded-xl border border-line bg-white px-3 text-sm font-semibold text-ink"><option value="en">English</option><option value="hi">हिन्दी</option></select></div><label className="mt-6 block text-left"><span className="text-xs font-bold text-ink-2">Transcript — review and correct it</span><textarea value={description} onChange={(event) => onDescription(event.target.value)} rows={5} maxLength={1200} placeholder="Your words will appear here. You can type instead." className="mt-1.5 w-full resize-y rounded-2xl border border-line bg-ground/60 p-4 text-sm leading-6 text-ink placeholder:text-ink-3" /></label></div>
}

function TextInput({ value, onChange, optional = false }: { value: string; onChange: (value: string) => void; optional?: boolean }) {
  return <label className="block"><span className="text-xs font-bold text-ink-2">What happened? {optional ? <span className="font-normal text-ink-3">(optional)</span> : null}</span><textarea value={value} onChange={(event) => onChange(event.target.value)} rows={6} maxLength={1200} placeholder="Describe the problem, how long it has been there, and why it needs attention…" className="mt-1.5 w-full resize-y rounded-2xl border border-line bg-ground/60 p-4 text-sm leading-6 text-ink placeholder:text-ink-3" /><span className="mt-1 block text-right text-[10px] text-ink-3">{value.length}/1200</span></label>
}

function IssuePicker({ value, onChange }: { value: IssueType | null; onChange: (issue: IssueType) => void }) {
  return <fieldset><legend className="text-xs font-bold text-ink-2">Issue category</legend><div className="mt-2 grid gap-2 sm:grid-cols-2">{ISSUES.map((item) => <button key={item.id} type="button" aria-pressed={value === item.id} onClick={() => onChange(item.id)} className={`rounded-xl border p-3 text-left transition-colors ${value === item.id ? 'border-brand bg-brand-soft text-brand-dark' : 'border-line bg-white text-ink hover:border-brand/50'}`}><span className="block text-sm font-bold">{item.label}</span><span className="mt-0.5 block text-xs opacity-75">{item.blurb}</span></button>)}</div></fieldset>
}

function PhotoPicker({ photo, busy, onPick, prominent = false }: { photo: PhotoState | null; busy: string | null; onPick: (file: File | undefined) => void; prominent?: boolean }) {
  return <div>{photo ? <figure className="overflow-hidden rounded-2xl border border-line bg-ground"><img src={photo.preview} alt="Selected civic issue" className="max-h-64 w-full object-cover" /><figcaption className="flex items-center justify-between gap-2 px-3 py-2 text-xs text-ink-3"><span><Icon name="check" className="mr-1 inline h-3.5 w-3.5 text-brand" />Ready · {photo.saved}</span><label className="cursor-pointer font-bold text-brand">Replace<input type="file" accept="image/*" capture="environment" className="sr-only" onChange={(event) => void onPick(event.target.files?.[0])} /></label></figcaption></figure> : <label className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-line bg-ground/60 text-center transition-colors hover:border-brand ${prominent ? 'min-h-64 p-8' : 'min-h-36 p-5'}`}><span className="icon-badge">{busy ? <Spinner className="h-5 w-5" /> : <Icon name="camera" className="h-5 w-5" />}</span><strong className="mt-3 text-sm text-ink">{busy ?? 'Take or choose a photo'}</strong><span className="mt-1 text-xs text-ink-3">JPEG, PNG, WebP or HEIC · resized on your device</span><input type="file" accept="image/*" capture="environment" className="sr-only" disabled={Boolean(busy)} onChange={(event) => void onPick(event.target.files?.[0])} /></label>}</div>
}

function ReviewComplaint({ mode, issue, description, photo, landmark, wardName, wardId, language, busy, sending, guestAlias, onLanguage, onEdit, onSubmit }: { mode: EntryMode; issue: IssueType; description: string; photo: PhotoState | null; landmark: string; wardName: string; wardId: string; language: 'en' | 'hi'; busy: string | null; sending: boolean; guestAlias: string | null; onLanguage: (language: 'en' | 'hi') => void; onEdit: (stage: 'details' | 'place') => void; onSubmit: () => void }) {
  const issueLabel = ISSUES.find((item) => item.id === issue)?.label ?? issue
  const subject = `${issueLabel} requiring attention — ${wardName}`
  const body = description.trim() || `I wish to report a ${issueLabel.toLowerCase()} issue in ${wardName}.`
  const mailto = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(`${body}\n\nWard: ${wardId}${landmark ? `\nLandmark: ${landmark}` : ''}`)}`
  return <section className="space-y-4"><div className="app-card overflow-hidden"><header className="flex flex-wrap items-start justify-between gap-3 border-b border-line bg-ground/50 p-5 sm:p-6"><div><p className="section-kicker">Human review</p><h2 className="mt-1 text-xl font-extrabold text-ink">Review your complaint</h2><p className="mt-1 text-sm text-ink-2">Check every detail. MERAWARD will not submit without your confirmation.</p></div><span className="inline-flex items-center gap-1.5 rounded-full bg-band-low-soft px-3 py-1 text-xs font-bold text-band-low"><Icon name="shield" className="h-4 w-4" /> You are in control</span></header><div className="grid gap-0 divide-y divide-line sm:grid-cols-2 sm:divide-x sm:divide-y-0"><ReviewField label="Issue" value={issueLabel} detail={`${METHODS[mode].short} report`} onEdit={() => onEdit('details')} /><ReviewField label="Ward" value={wardName} detail={wardId} onEdit={() => onEdit('place')} /></div><div className="border-t border-line p-5 sm:p-6"><div className="flex items-center justify-between gap-2"><span className="text-xs font-bold uppercase tracking-wide text-ink-3">Citizen's description</span><button type="button" onClick={() => onEdit('details')} className="text-xs font-bold text-brand">Edit</button></div><p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-ink">{body}</p>{landmark ? <p className="mt-2 text-xs text-ink-3">Near {landmark}</p> : null}{photo ? <div className="mt-4 flex items-center gap-3 rounded-xl bg-ground p-2"><img src={photo.preview} alt="Complaint evidence" className="h-14 w-16 rounded-lg object-cover" /><span className="text-xs font-semibold text-ink-2">1 evidence photo attached</span></div> : <p className="mt-4 rounded-xl bg-ground px-3 py-2 text-xs text-ink-3">No photo attached · text-only report</p>}</div><div className="border-t border-line bg-ground/55 p-5 sm:p-6"><fieldset><legend className="text-xs font-bold uppercase tracking-wide text-ink-3">Complaint language</legend><div className="mt-2 grid grid-cols-2 gap-2"><button type="button" onClick={() => onLanguage('en')} aria-pressed={language === 'en'} className={`rounded-xl border px-4 py-3 text-sm font-bold ${language === 'en' ? 'border-brand bg-brand-soft text-brand-dark' : 'border-line bg-white text-ink-2'}`}>English</button><button type="button" onClick={() => onLanguage('hi')} aria-pressed={language === 'hi'} className={`rounded-xl border px-4 py-3 text-sm font-bold ${language === 'hi' ? 'border-brand bg-brand-soft text-brand-dark' : 'border-line bg-white text-ink-2'}`}>हिन्दी</button></div></fieldset>{guestAlias ? <p className="mt-3 flex items-center gap-1.5 text-xs font-semibold text-ink-3"><Icon name="user" className="h-3.5 w-3.5" /> This report will be remembered for <strong className="text-ink-2">{guestAlias}</strong> on this device.</p> : null}</div></div>{sending ? <ProcessingStatus busy={busy} hasPhoto={Boolean(photo)} /> : null}<div className="grid gap-2 sm:grid-cols-[1fr_1.35fr]"><a href={mailto} aria-disabled={sending} className={`button-secondary inline-flex items-center justify-center gap-2 text-center ${sending ? 'pointer-events-none opacity-50' : ''}`}><Icon name="document" className="h-4 w-4" /> Open email draft</a><button type="button" disabled={sending} onClick={onSubmit} className="button-primary inline-flex items-center justify-center gap-2 disabled:opacity-60">{sending ? <><Spinner /> {busy ?? 'Submitting…'}</> : <>Submit through MERAWARD <Icon name="arrow" className="h-4 w-4" /></>}</button></div><DemoNotice>Opening an email draft does not file through MERAWARD. “Submit through MERAWARD” creates the public tracking record. Delivery remains in the configured demo outbox.</DemoNotice></section>
}

function ProcessingStatus({ busy, hasPhoto }: { busy: string | null; hasPhoto: boolean }) {
  const uploading = busy?.startsWith('Uploading') ?? false
  return <div className="processing-card" role="status" aria-live="polite"><div className="flex items-center gap-3"><Spinner className="h-5 w-5 text-brand" /><div><p className="text-sm font-extrabold text-ink">{busy ?? 'Submitting your complaint…'}</p><p className="mt-0.5 text-xs text-ink-3">Please keep this page open. Your report is being safely recorded.</p></div></div><ol className="mt-4 grid grid-cols-3 gap-2 text-[10px] font-bold"><li className={hasPhoto && uploading ? 'text-brand-dark' : 'text-ink-3'}>{hasPhoto ? '1. Upload evidence' : '1. Check details'}</li><li className={!uploading ? 'text-brand-dark' : 'text-ink-3'}>2. Create record</li><li className="text-ink-3">3. Prepare letter</li></ol></div>
}

function ReviewField({ label, value, detail, onEdit }: { label: string; value: string; detail: string; onEdit: () => void }) {
  return <div className="p-5 sm:p-6"><div className="flex items-center justify-between gap-2"><span className="text-xs font-bold uppercase tracking-wide text-ink-3">{label}</span><button type="button" onClick={onEdit} className="text-xs font-bold text-brand">Change</button></div><p className="mt-2 font-bold text-ink">{value}</p><p className="mt-0.5 font-mono text-xs text-ink-3">{detail}</p></div>
}

function Progress({ stage }: { stage: Stage }) {
  const current = stage === 'input' ? 0 : stage === 'details' ? 1 : stage === 'place' ? 2 : 3
  return <ol className="grid grid-cols-4 gap-2" aria-label="Complaint progress">{['Input', 'Details', 'Location', 'Review'].map((label, index) => <li key={label}><div className={`h-1.5 rounded-full ${index <= current ? 'bg-brand' : 'bg-line'}`} /><span className={`mt-1.5 block text-[10px] font-bold ${index <= current ? 'text-brand-dark' : 'text-ink-3'}`}>{label}</span></li>)}</ol>
}

function guessIssue(text: string): IssueType {
  const value = text.toLowerCase()
  if (/pothole|road|गड्ढ|सड़क/.test(value)) return 'POTHOLE'
  if (/light|lamp|streetlight|बत्ती|लाइट/.test(value)) return 'STREETLIGHT'
  if (/garbage|waste|trash|कूड़ा|कचरा/.test(value)) return 'GARBAGE'
  if (/water|drain|flood|पानी|नाली/.test(value)) return 'WATER'
  return 'OTHER'
}

function Submitted({ id, token }: { id: string; token: string }) {
  const complaint = useQuery({ queryKey: ['complaint', id], queryFn: () => api.complaint(id), refetchInterval: (query) => { const status = query.state.data?.draft_status; return status === 'DRAFTED' || status === 'SENT' || status === 'FAILED' ? false : 2000 }, staleTime: 0 })
  const drafting = complaint.data?.draft_status === 'PENDING' || complaint.isPending
  useEffect(() => { try { localStorage.setItem(`meraward:token:${id}`, token) } catch { /* The on-screen link remains available. */ } }, [id, token])
  return <div className="mx-auto max-w-2xl space-y-4"><div className="app-card p-7 text-center"><span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-band-low-soft text-band-low"><Icon name="check" className="h-7 w-7" /></span><p className="section-kicker mt-4">Submitted</p><h1 className="mt-1 text-2xl font-black tracking-tight text-ink">Your complaint is on the record.</h1><p className="mt-2 font-mono text-xs text-ink-3">{id}</p></div>{drafting ? <div className="app-card p-5" aria-live="polite"><div className="flex items-center gap-2"><Spinner className="text-brand" /><p className="text-sm font-bold text-ink">Preparing the formal bilingual letter…</p></div><p className="mt-1 text-sm text-ink-2">The complaint is already saved. This normally takes a few seconds.</p><div className="mt-4 space-y-2"><Skeleton className="h-4 w-4/5" /><Skeleton className="h-4 w-full" /><Skeleton className="h-4 w-3/5" /></div></div> : complaint.data ? <BilingualDraft subject={complaint.data.subject} en={complaint.data.body_en} hi={complaint.data.body_hi} /> : null}<div className="grid gap-2 sm:grid-cols-2"><Link to={`/c/${id}`} className="button-primary text-center">Track this complaint</Link><Link to={`/u/${token}?id=${encodeURIComponent(id)}`} className="button-secondary text-center">Your private update link</Link></div><DemoNotice>Keep the update link. It is the only way to change this complaint's status; the optional guest profile only remembers it on this device.</DemoNotice></div>
}

export function BilingualDraft({ subject, en, hi }: { subject: string | null; en: string | null; hi: string | null }) {
  const [lang, setLang] = useState<'en' | 'hi'>('en')
  const body = useMemo(() => (lang === 'en' ? en : hi), [lang, en, hi])
  if (!en && !hi) return null
  return <article className="app-card overflow-hidden"><header className="flex items-center gap-2 border-b border-line p-4"><span className="icon-badge"><Icon name="document" className="h-5 w-5" /></span><h2 className="min-w-0 flex-1 truncate text-sm font-bold text-ink">{subject ?? 'Your complaint'}</h2><div className="flex shrink-0 rounded-lg bg-ground p-0.5" role="tablist">{(['en', 'hi'] as const).map((code) => <button key={code} type="button" role="tab" aria-selected={lang === code} onClick={() => setLang(code)} className={`rounded-md px-2.5 py-1 text-xs font-bold ${lang === code ? 'bg-white text-ink shadow-sm' : 'text-ink-3'}`}>{code === 'en' ? 'English' : 'हिन्दी'}</button>)}</div></header><pre className="overflow-x-auto whitespace-pre-wrap p-5 font-sans text-sm leading-7 text-ink-2">{body}</pre></article>
}
