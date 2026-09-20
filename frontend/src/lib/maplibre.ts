import { setWorkerUrl } from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'

// Vite's dependency optimizer changes import.meta.url. Resolve the separate
// MapLibre 6 worker as an explicit asset in both development and production.
setWorkerUrl(workerUrl)

export * from 'maplibre-gl'
