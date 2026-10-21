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
    // Jade's theme, fun mode: purple + orange on cream — members take colors
    // in roster order, so Jade is purple and Hannah orange (mint and lime for
    // anyone after). Round Fredoka/Nunito type, chunky rounded blocks. Pinned
    // light (no toggle, nothing saved); the dev-only /styleguide's theme lab
    // can try other looks.
    ui({
      colors: { primary: '#8b5cf6', accent: '#ff8a3d', neutral: '#3b2a1e', danger: '#d93a3a' },
      fonts: { heading: 'Fredoka', body: 'Nunito', mono: 'Cascadia Code' },
      style: 'block',
      radius: 14,
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
