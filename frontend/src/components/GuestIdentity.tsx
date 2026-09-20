import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useGuest } from '../auth/GuestAuth'
import { Icon } from './Icon'

export function GuestIdentity() {
  const { profile, login, logout, updateAlias } = useGuest()
  const [open, setOpen] = useState(false)
  const [alias, setAlias] = useState('')
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => setAlias(profile?.alias ?? ''), [profile?.alias])
  useEffect(() => {
    if (!open) return
    const close = (event: MouseEvent) => {
      if (!panelRef.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [open])

  function loginGuest() {
    login()
    setOpen(true)
  }

  function saveAlias(event: FormEvent) {
    event.preventDefault()
    if (alias.trim().length < 2) return
    updateAlias(alias)
    setOpen(false)
  }

  if (!profile) {
    return (
      <button type="button" onClick={loginGuest} className="guest-login-button">
        <Icon name="user" className="h-4 w-4" />
        <span className="hidden sm:inline">Login as guest</span>
        <span className="sm:hidden">Login</span>
      </button>
    )
  }

  return (
    <div className="relative" ref={panelRef}>
      <button
        type="button"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
        className="guest-profile-button"
      >
        <span className="guest-avatar" aria-hidden="true">{profile.alias.slice(0, 1).toUpperCase()}</span>
        <span className="hidden max-w-24 truncate sm:block">{profile.alias}</span>
        <Icon name="chevron" className={`h-3.5 w-3.5 transition-transform ${open ? 'rotate-90' : ''}`} />
      </button>

      {open ? (
        <div role="dialog" aria-label="Guest profile" className="guest-panel">
          <div className="flex items-start gap-3 border-b border-line p-4">
            <span className="guest-avatar guest-avatar--large" aria-hidden="true">{profile.alias.slice(0, 1).toUpperCase()}</span>
            <div className="min-w-0">
              <p className="truncate text-sm font-extrabold text-ink">{profile.alias}</p>
              <p className="mt-0.5 text-[11px] leading-4 text-ink-3">Guest profile · saved only on this device</p>
            </div>
          </div>
          <form onSubmit={saveAlias} className="space-y-3 p-4">
            <label className="block">
              <span className="text-[11px] font-bold uppercase tracking-wide text-ink-3">Your display name</span>
              <input
                value={alias}
                onChange={(event) => setAlias(event.target.value)}
                minLength={2}
                maxLength={24}
                autoComplete="nickname"
                className="mt-1.5 min-h-11 w-full rounded-xl border border-line bg-ground px-3 text-sm font-semibold text-ink"
              />
            </label>
            <button type="submit" disabled={alias.trim().length < 2} className="button-primary w-full disabled:opacity-50">Save name</button>
          </form>
          {profile.complaintIds.length ? (
            <div className="border-t border-line px-4 py-3">
              <p className="text-[11px] font-bold uppercase tracking-wide text-ink-3">Your latest report</p>
              <Link to={`/c/${profile.complaintIds[0]}`} onClick={() => setOpen(false)} className="mt-1 block truncate font-mono text-xs font-bold text-brand underline underline-offset-2">
                {profile.complaintIds[0]}
              </Link>
            </div>
          ) : null}
          <button type="button" onClick={() => { logout(); setOpen(false) }} className="flex min-h-11 w-full items-center gap-2 border-t border-line px-4 text-left text-xs font-bold text-ink-2 hover:bg-ground">
            <Icon name="logout" className="h-4 w-4" /> Sign out on this device
          </button>
        </div>
      ) : null}
    </div>
  )
}
