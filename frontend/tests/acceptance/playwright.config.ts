import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: '.',
  use: {
    baseURL: process.env.BASE_URL ?? 'http://127.0.0.1:3030',
    viewport: { width: 390, height: 844 },
  },
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
})
