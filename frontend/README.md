# MeraWard frontend

React 18, TypeScript, Tailwind, TanStack Query, React Router 7 and MapLibre 6. The interface supports report intake, a review step, bilingual drafts, public tracking, private status links and a ward dashboard. Amrit led the original frontend work; team contributions are credited in the [root README](../README.md#team-and-contribution).

## Local development

The simplest full stack is `docker compose up --build` from the root, then **http://localhost:5174**. Source/public bind mounts and Windows-friendly polling provide Fast Refresh without rebuilding the frontend image.

For native development, use Node.js **22.12+ or 24**. Start the [native local API](../backend/README.md#run-it), then from this directory:

```bash
npm ci
npm run dev -- --port 5174 --strictPort
```

Put local settings in ignored `frontend/.env.local`:

```dotenv
VITE_API_BASE_URL=http://localhost:8101
VITE_LOCAL_DEMO=true
```

`VITE_API_BASE_URL` must identify a real API. Leaving it empty against a static SPA can return `index.html` with status 200; the client correctly rejects that as an invalid JSON response. `VITE_LOCAL_DEMO` displays the sandbox banner. Optional `VITE_BASEMAP_STYLE_URL` changes the MapLibre style; the default CARTO map needs internet access and retains its attribution.

## Routes

| Route | Purpose |
| --- | --- |
| `/` | Report entry points and public summary |
| `/ward` | Pin/location lookup and ward information |
| `/report?mode=voice`, `photo` or `write` | Evidence, issue, location and review before submission |
| `/c/:id` | Public letter, photo, ward and timeline |
| `/u/:token?id=:id` | Private token-authorized status changes |
| `/dashboard` | Map/heatmap, filters and ward leaderboard |
| `/about` | Dataset and index limits |

Speech capture depends on the browser. The transcript textbox remains available when the API is missing or recognition fails; no speech transcription service is required for typed reports. HEIC can fall back to the original upload because browsers may not decode it. Guest aliases are device-local and do not grant API permissions. Never include a private update URL in an issue or screenshot.

## Map and caching

MapLibre 6 is an ES module with a separate worker asset. [`src/lib/maplibre.ts`](src/lib/maplibre.ts) imports that asset with Vite's `?url` and calls `setWorkerUrl` before any map is created. Import runtime map APIs through that wrapper; direct initialization can leave Vite's optimized worker URL pointing to a missing file. Verify the actual map in a browser, not only the TypeScript build.

Maps and non-home routes load separately. PWA setup creates a manifest/service worker, precaches the app shell and caches selected map assets/tiles on use. It does not provide a complete offline complaint workflow: API writes and uncached basemap data need a connection. Historical Lighthouse/bundle figures do not apply automatically after a dependency update.

## Checks

```bash
npm run typecheck
npm run build
npm audit --omit=dev
```

Build checks TypeScript and generates the production service worker. CI also runs the production dependency audit. See [maintenance notes](../docs/MAINTENANCE.md) for the separately disclosed development-tool advisories. Browser verification should cover map-worker loading, text/photo intake, review, the actual queued letter, private-link status updates, unsupported-speech typed fallback and mobile overflow. A deployment needs an SPA rewrite for deep links; see [AWS setup](../docs/AWS_SETUP.md).
