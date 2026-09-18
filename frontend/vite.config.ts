import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'MERAWARD — know your ward',
        short_name: 'MERAWARD',
        description:
          "Find your Delhi ward, report a civic problem, and see which wards are being ignored.",
        theme_color: '#0E6E68',
        background_color: '#ffffff',
        display: 'standalone',
        start_url: '/',
        icons: [],
      },
      workbox: {
        // The API is never precached: a stale Neglect Index is worse than a spinner.
        navigateFallbackDenylist: [/^\/api/],
        globPatterns: ['**/*.{js,css,html,svg,woff2}'],
        // Precaching MapLibre would pull 800 kB over mobile data for a visitor
        // who only reads /about, undoing the code split. It is cached on first
        // use instead, and then served from cache on every later visit.
        globIgnores: ['**/maplibre-*.js'],
        runtimeCaching: [
          {
            urlPattern: /\/assets\/maplibre-.*\.js$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'maplibre',
              expiration: { maxEntries: 2, maxAgeSeconds: 60 * 60 * 24 * 30 },
            },
          },
          {
            // Basemap tiles: served from cache while revalidating, so panning
            // over ground you have already seen costs nothing.
            urlPattern: /^https:\/\/[a-z0-9.]*basemaps\.cartocdn\.com\/.*/i,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'basemap-tiles',
              expiration: { maxEntries: 600, maxAgeSeconds: 60 * 60 * 24 * 7 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],
      },
    }),
  ],
  build: {
    outDir: 'dist',
    // Source maps are not shipped: they were 2.7 MB, dwarfing the app itself,
    // and a public demo has no use for them.
    sourcemap: false,
    cssMinify: true,
    rollupOptions: {
      output: {
        manualChunks: {
          // MapLibre is the single heaviest dependency. Splitting it into its
          // own chunk means it is fetched once and cached across every route
          // that shows a map, and never fetched at all by someone who only
          // reads /about.
          maplibre: ['maplibre-gl'],
          react: ['react', 'react-dom', 'react-router-dom'],
          query: ['@tanstack/react-query'],
        },
      },
    },
  },
})
