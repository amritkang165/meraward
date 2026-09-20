import { lazy, Suspense } from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import Home from './routes/Home'
import { PageLoader } from './components/states'
import { Icon } from './components/Icon'
import { GuestIdentity } from './components/GuestIdentity'

/**
 * Every route below the home page is split out.
 *
 * Home is the entry point and is bundled with the shell so the first paint
 * needs one request. Everything else — and in particular anything that pulls in
 * MapLibre, which is the single heaviest dependency we ship — loads only when
 * someone navigates to it.
 */
const Ward = lazy(() => import('./routes/Ward'))
const Report = lazy(() => import('./routes/Report'))
const Dashboard = lazy(() => import('./routes/Dashboard'))
const ComplaintDetail = lazy(() => import('./routes/ComplaintDetail'))
const StatusUpdate = lazy(() => import('./routes/StatusUpdate'))
const About = lazy(() => import('./routes/About'))
const NotFound = lazy(() => import('./routes/NotFound'))

const NAV = [
  { to: '/', label: 'Home', end: true },
  { to: '/ward', label: 'My ward', end: false },
  { to: '/dashboard', label: 'Dashboard', end: false },
  { to: '/about', label: 'About', end: false },
]

export default function App() {
  return (
    <div className="flex min-h-dvh flex-col bg-ground">
      <header className="sticky top-0 z-30 border-b border-white/70 bg-white/82 shadow-[0_1px_0_rgba(15,23,42,0.03)] backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-2.5 sm:py-3">
          <NavLink to="/" className="group flex items-center gap-2.5 text-ink">
            <span aria-hidden="true" className="brand-mark">
              <span className="brand-mark__road" />
            </span>
            <span className="leading-none">
              <span className="block text-sm font-black tracking-[-0.02em] sm:text-base">MERAWARD</span>
              <span className="mt-1 hidden text-[9px] font-semibold uppercase tracking-[0.16em] text-ink-3 sm:block">My city · My voice</span>
            </span>
          </NavLink>
          <nav className="ml-auto hidden gap-1 text-sm md:flex" aria-label="Main">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `rounded-xl px-3 py-2 font-semibold transition-colors ${
                    isActive
                      ? 'bg-brand-soft font-semibold text-brand-dark'
                      : 'text-ink-2 hover:bg-surface-2'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <NavLink
            to="/ward"
            className="ml-auto hidden items-center gap-2 rounded-xl border border-line bg-ground/80 px-3 py-2 text-xs font-semibold text-ink-2 sm:flex md:ml-2"
          >
            <Icon name="location" className="h-4 w-4 text-brand" />
            <span><span className="block text-[9px] uppercase tracking-wide text-ink-3">Demo location</span>Delhi · Find ward</span>
          </NavLink>
          <GuestIdentity />
          <NavLink to="/report" className="ml-auto inline-flex min-h-10 items-center gap-1.5 rounded-xl bg-ink px-3.5 text-xs font-bold text-white sm:ml-0">
            Report <Icon name="arrow" className="h-3.5 w-3.5" />
          </NavLink>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-5 sm:py-7">
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/ward" element={<Ward />} />
            <Route path="/report" element={<Report />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/c/:id" element={<ComplaintDetail />} />
            <Route path="/u/:token" element={<StatusUpdate />} />
            <Route path="/about" element={<About />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </main>

      <nav className="sticky bottom-0 z-30 grid grid-cols-4 border-t border-line bg-white/94 px-2 pb-[max(.4rem,env(safe-area-inset-bottom))] pt-1.5 backdrop-blur-xl md:hidden" aria-label="Mobile navigation">
        {NAV.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => `flex min-h-12 flex-col items-center justify-center rounded-xl text-[10px] font-bold ${isActive ? 'bg-brand-soft text-brand-dark' : 'text-ink-3'}`}>
            {item.label}
          </NavLink>
        ))}
      </nav>

      <footer className="border-t border-line bg-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-5 text-xs leading-relaxed text-ink-3 sm:flex-row sm:items-center sm:justify-between">
          <span>
          Complaint data on this deployment is generated for demonstration and is labelled as such.
          The Ward Neglect Index scores a <strong>ward</strong>, never a person.{' '}
          <NavLink to="/about" className="font-medium text-brand underline underline-offset-2">
            Sources and methodology
          </NavLink>
          .</span>
          <span className="font-semibold text-ink-2">Built on AWS · Delhi demo</span>
        </div>
      </footer>
    </div>
  )
}
