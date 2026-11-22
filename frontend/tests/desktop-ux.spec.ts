import { test, expect, type Locator, type Page } from '@playwright/test'
import { go, sample, unlock } from './helpers'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'

async function inViewport(page: Page, locator: Locator) {
  await expect(locator).toBeVisible()
  const box = await locator.boundingBox()
  expect(box).not.toBeNull()
  expect(box!.y).toBeGreaterThanOrEqual(0)
  expect(box!.y + box!.height).toBeLessThanOrEqual(page.viewportSize()!.height)
  const unobscured = await locator.evaluate(element => {
    const box = element.getBoundingClientRect()
    const top = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2)
    return top === element || element.contains(top)
  })
  expect(unobscured).toBe(true)
}

for (const viewport of [{ width: 1280, height: 720 }, { width: 1366, height: 768 }, { width: 1600, height: 900 }, { width: 1920, height: 1080 }, { width: 1093, height: 614 }]) {
  test(`task actions are reachable at ${viewport.width}x${viewport.height}`, async ({ page }, testInfo) => {
    async function capture(route: string) {
      if (testInfo.project.name !== 'desktop-1366' || ![1280, 1600].includes(viewport.width)) return
      const directory = path.resolve('qa/phase4a1/after')
      await mkdir(directory, { recursive: true })
      for (const dismiss of await page.getByRole('button', { name: /^Dismiss / }).all()) await dismiss.click()
      await page.screenshot({ path: path.join(directory, `${viewport.width}x${viewport.height}-${route}.png`), animations: 'disabled' })
    }
    await page.setViewportSize(viewport)
    await go(page, 'sign')
    await inViewport(page, page.getByRole('button', { name: 'Choose PDF', exact: true }))
    await expect(page.locator('.dropzone')).toHaveCSS('font-size', '14px')
    expect((await page.locator('.dropzone').boundingBox())!.height).toBeLessThanOrEqual(150)
    await sample(page)
    await inViewport(page, page.getByRole('button', { name: 'Preview unlock', exact: true }))
    await unlock(page)
    await expect(page.getByRole('button', { name: 'Continue to review', exact: true })).toBeFocused()
    await page.getByRole('button', { name: 'Continue to review', exact: true }).click()
    const sign = page.getByRole('button', { name: 'Sign PDF', exact: true })
    await inViewport(page, sign); await expect(sign).toBeDisabled()
    await expect(page.getByRole('region', { name: 'Signing actions' })).toContainText('Use a desktop build with signing support')
    await capture('sign-review')
    await page.getByRole('button', { name: 'Review and sign step', exact: true }).focus()
    await page.getByRole('main').evaluate(element => { element.scrollTop = element.scrollHeight })
    await inViewport(page, sign)
    await inViewport(page, page.getByRole('navigation'))
    await go(page, 'verify')
    await inViewport(page, page.getByLabel('Public-key source'))
    await inViewport(page, page.getByRole('button', { name: 'Verify PDF', exact: true }))
    await expect(page.getByRole('button', { name: 'Verify PDF', exact: true })).toBeDisabled()
    await capture('verify')
    await go(page, 'vault')
    await inViewport(page, page.getByRole('button', { name: 'Lock demo vault', exact: true }))
    await page.getByRole('button', { name: 'Lock demo vault', exact: true }).click()
    await inViewport(page, page.getByRole('button', { name: 'Preview unlock', exact: true }))
    await inViewport(page, page.getByRole('button', { name: 'Public key details', exact: true }))
    await inViewport(page, page.getByRole('button', { name: 'Change password', exact: true }))
    await capture('vault')
    for (const route of ['dashboard', 'sign', 'verify', 'vault', 'settings']) {
      await go(page, route)
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(viewport.width)
      expect(await page.getByRole('main').evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true)
      for (const label of await page.locator('.page-heading p, .field-label, .field-hint, .nav-item span').all()) {
        expect(await label.evaluate(element => Number.parseFloat(getComputedStyle(element).fontSize))).toBeGreaterThanOrEqual(12)
      }
    }
  })
}

test('signing has one expanded step, editable summaries and no genuine sign action', async ({ page }) => {
  await go(page, 'sign')
  await expect(page.locator('.step-body:visible')).toHaveCount(1)
  await sample(page)
  await expect(page.getByRole('button', { name: 'Choose PDF step', exact: true })).toHaveAttribute('aria-expanded', 'false')
  await expect(page.locator('.step-body:visible')).toHaveCount(1)
  await unlock(page)
  await page.getByRole('button', { name: 'Continue to review', exact: true }).click()
  await expect(page.locator('.step-body:visible')).toHaveCount(1)
  await page.getByRole('button', { name: 'Choose PDF step', exact: true }).click()
  await page.getByRole('button', { name: 'Remove selected document' }).click()
  await expect(page.getByRole('button', { name: 'Select vault step', exact: true })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Review and sign step', exact: true })).toBeDisabled()
})

test('selecting a PDF never verifies it and examples are a separate explicit action', async ({ page }) => {
  await go(page, 'verify'); await sample(page)
  await expect(page.getByRole('button', { name: 'Verify PDF', exact: true })).toBeDisabled()
  await expect(page.locator('.verification-layer')).not.toContainText(['Example: pass', 'Example: pass'])
  await expect(page.getByLabel('Example scenario')).not.toBeVisible()
  await page.getByText('Explore example results', { exact: true }).click()
  await page.getByRole('button', { name: 'Preview verification', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Example: both layers pass' })).toBeVisible()
  await expect(page.locator('.verification-overview')).toContainText('No cryptographic verification was performed')
})

test('125 percent device-scale approximation preserves reachable actions', async ({ browser }, testInfo) => {
  const context = await browser.newContext({ baseURL: 'http://127.0.0.1:4173', viewport: { width: 1093, height: 614 }, deviceScaleFactor: 1.25 })
  try {
    const page = await context.newPage()
    await go(page, 'sign'); await sample(page); await unlock(page)
    await page.getByRole('button', { name: 'Continue to review', exact: true }).click()
    expect(await page.evaluate(() => devicePixelRatio)).toBe(1.25)
    await inViewport(page, page.getByRole('button', { name: 'Sign PDF', exact: true }))
    await expect(page.getByRole('button', { name: 'Sign PDF', exact: true })).toBeDisabled()
    const directory = path.resolve('qa/phase4a1/after')
    await mkdir(directory, { recursive: true })
    for (const dismiss of await page.getByRole('button', { name: /^Dismiss / }).all()) await dismiss.click()
    await page.screenshot({ path: path.join(directory, `${testInfo.project.name}-scale125-sign.png`), animations: 'disabled' })
  } finally { await context.close() }
})
