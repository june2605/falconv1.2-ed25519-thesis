import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 3,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:4173',
    channel: 'msedge',
    headless: true,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'desktop-1366', use: { viewport: { width: 1366, height: 768 } } },
    { name: 'desktop-1920', use: { viewport: { width: 1920, height: 1080 } } },
  ],
  webServer: { command: 'npm run preview', url: 'http://127.0.0.1:4173', reuseExistingServer: !process.env.CI },
})
