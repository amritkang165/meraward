import { lazy, Suspense } from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import Home from './routes/Home'
import { LoadingCard } from './components/states'

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
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-30 border-b border-line bg-surface/90 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-2.5">
          <NavLink to="/" className="flex items-center gap-2 font-bold tracking-tight text-ink">
            <span aria-hidden="true" className="inline-block h-2.5 w-2.5 rounded-full bg-brand" />
            MERAWARD
          </NavLink>
          <nav className="ml-auto flex gap-1 text-sm" aria-label="Main">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `rounded-lg px-2.5 py-1.5 transition-colors ${
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
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-5">
        <Suspense fallback={<LoadingCard />}>
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

      <footer className="border-t border-line bg-surface">
        <div className="mx-auto max-w-5xl px-4 py-4 text-xs leading-relaxed text-ink-3">
          Complaint data on this deployment is generated for demonstration and is labelled as such.
          The Ward Neglect Index scores a <strong>ward</strong>, never a person.{' '}
          <NavLink to="/about" className="font-medium text-brand underline underline-offset-2">
            Sources and methodology
          </NavLink>
          .
        </div>
      </footer>
    </div>
  )
}
