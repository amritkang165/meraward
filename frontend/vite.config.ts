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
        // The API is never cached: a stale Neglect Index is worse than a spinner.
        navigateFallbackDenylist: [/^\/api/],
        globPatterns: ['**/*.{js,css,html,svg,woff2}'],
      },
    }),
  ],
  build: { outDir: 'dist', sourcemap: true },
})
