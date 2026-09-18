import { NavLink, Route, Routes } from 'react-router-dom'
import Home from './routes/Home'
import Ward from './routes/Ward'
import About from './routes/About'
import { Placeholder } from './routes/Placeholder'

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
                    isActive ? 'bg-brand-soft font-semibold text-brand-dark' : 'text-ink-2 hover:bg-surface-2'
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
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/ward" element={<Ward />} />
          <Route path="/about" element={<About />} />
          <Route
            path="/report"
            element={
              <Placeholder
                title="Report an issue"
                blurb="Photo, one tap, and the complaint drafts itself in Hindi and English."
                next={[
                  'Step 1 — pick the issue type',
                  'Step 2 — take or choose a photo, uploaded straight to S3',
                  'Step 3 — review the bilingual draft and submit',
                ]}
              />
            }
          />
          <Route
            path="/dashboard"
            element={
              <Placeholder
                title="Accountability dashboard"
                blurb="Every report across Delhi, and which wards are being ignored."
                next={['Complaint heatmap', 'Ward Neglect Index leaderboard', 'Issue and status filters']}
              />
            }
          />
          <Route
            path="/c/:id"
            element={
              <Placeholder
                title="Complaint"
                blurb="The shareable record of a single report."
                next={['Photo and location', 'The drafted letter in Hindi and English', 'Status timeline']}
              />
            }
          />
          <Route
            path="/u/:token"
            element={
              <Placeholder
                title="Update this complaint"
                blurb="Acknowledge it, mark it resolved, or say it's still broken."
                next={['Acknowledge', 'Resolve', 'Still broken']}
              />
            }
          />
          <Route
            path="*"
            element={
              <Placeholder
                title="Page not found"
                blurb="That link doesn't lead anywhere in MERAWARD."
                next={[]}
              />
            }
          />
        </Routes>
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
