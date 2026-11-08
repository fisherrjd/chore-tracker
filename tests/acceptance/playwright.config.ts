import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: '.',
  testMatch: /.*\.spec\.ts/,
  retries: 0,
  use: { baseURL: process.env.BASE_URL, trace: 'retain-on-failure', screenshot: 'only-on-failure' },
})
