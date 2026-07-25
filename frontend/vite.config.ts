import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// one port per app — backend runs on 3030, this dev server on 3031
const PORT = 3031

export default defineConfig({
  plugins: [vue(), tailwindcss()],
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
