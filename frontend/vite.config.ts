import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import ui from '@fisherrjd/ui/vite'

// one port per app — backend runs on 3030, this dev server on 3031
const PORT = 3031

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
    // Jade's theme, lagoon + block: teal and warm yellow, chunky outlines and
    // hard shadows, Cascadia Code headings. Pinned light (no toggle, nothing
    // saved); the dev-only /styleguide's theme lab can try other looks.
    ui({
      palette: 'lagoon',
      fonts: { heading: 'Cascadia Code', mono: 'Cascadia Code' },
      style: 'block',
      radius: 0,
      defaultMode: 'light',
      lockMode: true,
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    outDir: './dist',
  },
  preview: {
    port: PORT,
  },
  server: {
    host: '0.0.0.0',
    allowedHosts: true,
    port: PORT,
    proxy: {
      '/api': {
        target: process.env.VITE_BACKEND ?? 'http://localhost:3030',
        changeOrigin: true,
      },
    },
  },
})
