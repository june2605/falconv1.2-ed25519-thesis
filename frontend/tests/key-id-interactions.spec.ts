import { test, expect, type Page } from '@playwright/test'
import { go } from './helpers'
import { responsiveHost, publicId } from './support/native-responsive-host'

const nextId = 'hybrid-v1:' + 'fedcba9876543210'.repeat(4)

async function setup(page: Page, delayed = false) {
  await responsiveHost(page)
  await page.clock.install()
  await page.clock.pauseAt(new Date(Date.now() + 60_000))
  await page.addInitScript(({ delayed }) => {
    const active = new Set<number>(), set = window.setTimeout.bind(window), clear = window.clearTimeout.bind(window)
    window.setTimeout = ((handler: TimerHandler, delay?: number, ...args: unknown[]) => {
      if (delay !== 2000 || typeof handler !== 'function') return set(handler, delay, ...args)
      const handle = set(() => { active.delete(handle); handler(...args) }, delay)
      active.add(handle)
      return handle
    }) as typeof window.setTimeout
    window.clearTimeout = ((handle?: number) => { active.delete(handle!); return clear(handle) }) as typeof window.clearTimeout
    Object.assign(window, { __feedbackTimers: active })
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: {
      writeText: async (value: string) => {
        Object.assign(window, { __copiedId: value })
        if (delayed) await new Promise<void>((resolve, reject) => Object.assign(window, { __finishCopy: resolve, __failCopy: reject }))
      },
    } })
  }, { delayed })
  await go(page, 'verify')
  await expect(page.getByRole('heading', { name: 'HYBRID VALID', exact: true })).toBeVisible()
  return page.locator('.hybrid-key-id').first()
}

async function changePair(page: Page) {
  await page.evaluate(nextId => {
    const host = window as unknown as { __responsiveKeySource: Record<string, unknown> }
    host.__responsiveKeySource = { ...host.__responsiveKeySource, keySourceId: '7'.repeat(32), hybridKeyId: nextId }
  }, nextId)
  await page.getByRole('button', { name: 'Choose encrypted vault', exact: true }).click()
  await expect(page.locator('.key-id-compact')).toHaveText('hybrid-v1:fedcba98…76543210')
}

test('copy confirmation expires after two seconds and repeated clicks restart it', async ({ page }) => {
  const id = await setup(page), copy = id.getByRole('button', { name: 'Copy full ID', exact: true })
  await copy.click()
  await expect(copy).toContainText('Full ID copied.')
  await expect(id.getByRole('status')).toHaveText('Full ID copied.')
  expect(await page.evaluate(() => (window as unknown as { __copiedId: string }).__copiedId)).toBe(publicId)
  await page.clock.runFor(1500)
  await copy.click()
  await page.clock.runFor(1000)
  await expect(copy).toContainText('Full ID copied.')
  await page.clock.runFor(1001)
  await expect(copy).toHaveText('Copy full ID')
  await expect(id.getByRole('status')).toBeEmpty()
  expect(await page.evaluate(() => (window as unknown as { __feedbackTimers: Set<number> }).__feedbackTimers.size)).toBe(0)
})

test('feedback leaves the compact row and copy button geometry unchanged at every target size', async ({ page }) => {
  const id = await setup(page)
  for (const [width, height] of [[960, 600], [1100, 700], [1177, 740], [1280, 800], [1366, 768], [1440, 900], [1920, 1080]]) {
    await page.setViewportSize({ width, height })
    await id.scrollIntoViewIfNeeded()
    const copy = id.getByRole('button', { name: 'Copy full ID', exact: true })
    const before = await id.boundingBox(), buttonBefore = await copy.boundingBox()
    await copy.click()
    await expect(copy).toContainText('Full ID copied.')
    const after = await id.boundingBox(), buttonAfter = await copy.boundingBox()
    expect(after!.height).toBe(before!.height)
    expect(after!.width).toBe(before!.width)
    expect(buttonAfter!.width).toBe(buttonBefore!.width)
    await page.clock.runFor(2001)
    await expect(copy).toHaveText('Copy full ID')
    expect((await id.boundingBox())!.height).toBe(before!.height)
  }
})

test('keyboard disclosure state toggles with a stable label and a new pair clears expansion and feedback', async ({ page }) => {
  const id = await setup(page), disclosure = id.getByRole('button', { name: 'View full ID', exact: true })
  await expect(disclosure).toHaveText('View full ID')
  await disclosure.focus(); await page.keyboard.press('Enter')
  await expect(disclosure).toHaveText('View full ID')
  await expect(disclosure).toHaveAttribute('aria-expanded', 'true')
  await expect(id.locator('.key-id-full')).toBeVisible()
  await expect(id.locator('.key-id-full')).toHaveText(publicId)
  await disclosure.click()
  await expect(disclosure).toHaveText('View full ID')
  await expect(disclosure).toHaveAttribute('aria-expanded', 'false')
  await expect(id.locator('.key-id-full')).not.toBeVisible()
  await disclosure.focus(); await page.keyboard.press('Enter')
  await page.keyboard.press('Space')
  await expect(disclosure).toHaveText('View full ID')
  await expect(id.locator('.key-id-full')).not.toBeVisible()
  await disclosure.click()
  await id.getByRole('button', { name: 'Copy full ID', exact: true }).click()
  await expect(id.getByRole('status')).toHaveText('Full ID copied.')
  await changePair(page)
  await expect(disclosure).toHaveText('View full ID')
  await expect(id.locator('.key-id-full')).not.toBeVisible()
  await expect(id.getByRole('status')).toBeEmpty()
  await id.getByRole('button', { name: 'Copy full ID', exact: true }).click()
  expect(await page.evaluate(() => (window as unknown as { __copiedId: string }).__copiedId)).toBe(nextId)
})

for (const outcome of ['resolve', 'reject']) test(`late clipboard ${outcome} cannot affect a newly selected pair`, async ({ page }) => {
  const id = await setup(page, true)
  await id.getByRole('button', { name: 'Copy full ID', exact: true }).click()
  await changePair(page)
  await page.evaluate(outcome => {
    const host = window as unknown as { __finishCopy: () => void; __failCopy: (error: Error) => void }
    if (outcome === 'resolve') host.__finishCopy(); else host.__failCopy(new Error('clipboard denied'))
  }, outcome)
  await page.clock.runFor(1)
  await expect(id.getByRole('status')).toBeEmpty()
  await expect(id.getByRole('button', { name: 'View full ID', exact: true })).toHaveAttribute('aria-expanded', 'false')
  await expect(id.locator('.key-id-full')).not.toBeVisible()
})

test('unmount cancels feedback timers and remount starts collapsed without stale announcements', async ({ page }) => {
  const id = await setup(page)
  await id.getByRole('button', { name: 'Copy full ID', exact: true }).click()
  expect(await page.evaluate(() => (window as unknown as { __feedbackTimers: Set<number> }).__feedbackTimers.size)).toBe(1)
  await page.getByRole('link', { name: 'Settings', exact: true }).click()
  await expect.poll(() => page.evaluate(() => (window as unknown as { __feedbackTimers: Set<number> }).__feedbackTimers.size)).toBe(0)
  await page.clock.runFor(2500)
  await page.getByRole('link', { name: 'Verify Signature', exact: true }).click()
  await expect(id.getByRole('status')).toBeEmpty()
  await expect(id.getByRole('button', { name: 'View full ID', exact: true })).toHaveAttribute('aria-expanded', 'false')
  await expect(id.locator('.key-id-full')).not.toBeVisible()
})
