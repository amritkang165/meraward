import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

const STORAGE_KEY = 'meraward:guest:v1'
const MAX_COMPLAINTS = 20

export type GuestProfile = {
  alias: string
  createdAt: string
  complaintIds: string[]
}

type GuestContextValue = {
  profile: GuestProfile | null
  login: () => GuestProfile
  logout: () => void
  updateAlias: (alias: string) => void
  rememberComplaint: (complaintId: string) => void
}

const GuestContext = createContext<GuestContextValue | null>(null)

function readProfile(): GuestProfile | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<GuestProfile>
    if (typeof parsed.alias !== 'string' || !parsed.alias.trim()) return null
    return {
      alias: parsed.alias.slice(0, 24),
      createdAt: typeof parsed.createdAt === 'string' ? parsed.createdAt : new Date().toISOString(),
      complaintIds: Array.isArray(parsed.complaintIds)
        ? parsed.complaintIds.filter((id): id is string => typeof id === 'string').slice(0, MAX_COMPLAINTS)
        : [],
    }
  } catch {
    return null
  }
}

function saveProfile(profile: GuestProfile | null) {
  try {
    if (profile) localStorage.setItem(STORAGE_KEY, JSON.stringify(profile))
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    // Private browsing can deny storage. The in-memory guest still works.
  }
}

function makeAlias() {
  const values = new Uint32Array(1)
  crypto.getRandomValues(values)
  return `user${String(1000 + (values[0] % 9000))}`
}

export function GuestProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<GuestProfile | null>(readProfile)

  const login = useCallback(() => {
    if (profile) return profile
    const next = { alias: makeAlias(), createdAt: new Date().toISOString(), complaintIds: [] }
    setProfile(next)
    saveProfile(next)
    return next
  }, [profile])

  const logout = useCallback(() => {
    setProfile(null)
    saveProfile(null)
  }, [])

  const updateAlias = useCallback((rawAlias: string) => {
    const alias = rawAlias.replace(/\s+/g, ' ').trim().slice(0, 24)
    if (alias.length < 2) return
    setProfile((current) => {
      if (!current) return current
      const next = { ...current, alias }
      saveProfile(next)
      return next
    })
  }, [])

  const rememberComplaint = useCallback((complaintId: string) => {
    setProfile((current) => {
      if (!current) return current
      const complaintIds = [complaintId, ...current.complaintIds.filter((id) => id !== complaintId)].slice(0, MAX_COMPLAINTS)
      const next = { ...current, complaintIds }
      saveProfile(next)
      return next
    })
  }, [])

  const value = useMemo(
    () => ({ profile, login, logout, updateAlias, rememberComplaint }),
    [login, logout, profile, rememberComplaint, updateAlias],
  )

  return <GuestContext.Provider value={value}>{children}</GuestContext.Provider>
}

export function useGuest() {
  const value = useContext(GuestContext)
  if (!value) throw new Error('useGuest must be used inside GuestProvider')
  return value
}
