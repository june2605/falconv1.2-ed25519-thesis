import { test, expect } from '@playwright/test'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'
import { examples, go, review, sample, unlock } from './helpers'

test('capture the five screens and native-entry dialog', async ({ page }, testInfo) => {
  const directory = path.resolve('qa/phase4a1/after')
  await mkdir(directory, { recursive: true })
  async function capture(name: string) {
    for (const button of await page.getByRole('button', { name: /^Dismiss / }).all()) await button.click()
    await page.locator('main').evaluate(element => element.scrollTo({ top: 0, behavior: 'instant' }))
    await page.evaluate(() => document.fonts.ready)
    await expect(page.locator('body')).toBeVisible()
    await page.screenshot({ path: path.join(directory, `${testInfo.project.name}-${name}.png`), animations: 'disabled' })
  }
  for (const theme of ['light', 'dark']) {
    await go(page, 'settings')
    await page.getByRole('radio', { name: theme === 'light' ? 'Light' : 'Dark', exact: true }).check()
    for (const route of ['dashboard', 'sign', 'verify', 'vault', 'settings']) {
      await go(page, route)
      await capture(`${route}-${theme}`)
    }
  }
  await go(page, 'settings')
  await page.getByRole('radio', { name: 'Light', exact: true }).check()
  await go(page, 'dashboard')
  await page.getByRole('link', { name: 'Sign Document', exact: true }).click()
  await sample(page); await capture('sign-vault-step'); await unlock(page); await review(page); await capture('sign-ready')
  await page.getByRole('link', { name: 'Verify Signature', exact: true }).click()
  await sample(page); await examples(page); await page.getByRole('button', { name: 'Preview verification' }).click()
  await expect(page.getByRole('heading', { name: 'Example: both layers pass' })).toBeVisible()
  await capture('verify-example')
  await page.getByRole('link', { name: 'Key Vault', exact: true }).click(); await capture('vault')
  await page.getByRole('button', { name: 'Change password', exact: true }).click(); await capture('native-entry')
  await page.keyboard.press('Escape')
  await page.getByRole('link', { name: 'Settings', exact: true }).click()
  await page.getByRole('radio', { name: 'Dark', exact: true }).check(); await capture('settings-dark-selected')
})
