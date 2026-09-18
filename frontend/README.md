# MERAWARD — frontend

React 18 · Vite · TypeScript · Tailwind v4 · MapLibre GL JS · TanStack Query.
Mobile-first PWA, deployed on AWS Amplify Hosting. **Owner: Amrit.**

```bash
npm install
cp .env.example .env     # set VITE_API_BASE_URL to the deployed API stage
npm run dev              # dev server
npm run build            # typecheck + production build
npm run typecheck        # types only
```

## Routes

All built.

| Route | What it does |
|---|---|
| `/` | Hero, how-it-works, entry points |
| `/ward` | Map with a draggable pin → ward card + banded Neglect Index gauge. Accepts `?ward=DEL-0042` |
| `/report` | Three steps — issue type → photo → place — then a polling processing view |
| `/dashboard` | Heatmap or points, status/issue filters, paged leaderboard |
| `/c/:id` | Complaint detail: photo, bilingual letter, status timeline |
| `/u/:token` | Magic-link status update. Needs `?id=<complaint_id>` |
| `/about` | Data provenance, sources, licences, index methodology |

## Layout

```
src/
  api/          client.ts (fetch + typed errors), types.ts (mirrors the API)
  components/   MapView, ComplaintsMap, NeglectGauge, states
  lib/          useDebounced, image compression
  routes/       one file per route
```

`src/api/types.ts` mirrors the backend exactly. **The committed backend tests in
`backend/tests/` are the specification** — where a type here disagrees with a test
there, the test is right.

## Things that will bite you

- **Amplify needs an SPA rewrite** (`/<*>` → `/index.html`) or every deep link 404s,
  including `/ward`, `/c/:id` and `/u/:token`.
- **Verify basemap tiles from the deployed origin**, not localhost — provider referrer
  rules bite exactly there.
- **Record and test the demo on Android Chrome.** iOS Safari's camera and
  `MediaRecorder` behaviour is its own afternoon.
- A 2xx response whose body is not JSON is treated as an error, not an empty success.
  That is deliberate: with `VITE_API_BASE_URL` unset, requests hit the SPA fallback and
  get `index.html` back with a 200.

## Performance notes

Decisions here exist for a measured reason, not by habit.

| Choice | Why |
|---|---|
| MapLibre in its own chunk, loaded per route | 801 kB that `/` and `/about` never fetch |
| Excluded from service-worker precache | Precache went 1,119 KiB → 336 KiB |
| Client-side photo compression | A 6 MB phone photo becomes ~300–600 kB before upload |
| Debounced pin → ward lookup | Otherwise one API call per animation frame while dragging |
| GeoJSON layers, not DOM markers | Hundreds of pins draw on the GPU instead of the main thread |
| Leaderboard pages 25 at a time; filters run client-side | Changing a filter costs no request |

Lighthouse (mobile, simulated throttling): `/` **100 / 100 / 100 / 100**,
`/about` 95, `/dashboard` 86, `/ward` 80 — accessibility, best practices and SEO are
100 on every page.
