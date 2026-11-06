import { test, expect, type Page } from '@playwright/test'
import { mkdir } from 'node:fs/promises'
import { go } from './helpers'
import { responsiveHost, publicId } from './support/native-responsive-host'

const sizes = [[960, 600], [1100, 700], [1280, 800], [1366, 768], [1440, 900], [1920, 1080]]
const side = (page: Page) => page.getByRole('complementary', { name: 'Workspace sidebar', exact: true })
const auto = (page: Page) => page.getByRole('button', { name: 'Automatic sidebar', exact: true })
async function start(page: Page, width = 1100, height = 700) {
  await responsiveHost(page)
  await page.setViewportSize({ width, height }); await go(page, 'verify')
  await page.mouse.move(30, 180)
  await expect(side(page)).toHaveAttribute('data-expanded', 'true')
}
async function freeze(page: Page) {
  await page.clock.install(); await page.clock.pauseAt(new Date(Date.now() + 60000))
}

test('Auto preserves expansion through every route at all target sizes and retains native workflow state', async ({ page }) => {
  test.setTimeout(60000)
  await start(page)
  await page.getByRole('link', { name: 'Sign Document', exact: true }).click()
  await page.getByRole('button', { name: 'Choose PDF', exact: true }).click()
  await page.getByRole('button', { name: 'Continue to review', exact: true }).click()
  for (const [width, height] of sizes) {
    await page.mouse.move(width - 20, 170)
    await page.setViewportSize({ width, height })
    await page.mouse.move(width - 20, 170)
    await expect(side(page)).toHaveAttribute('data-expanded', 'false')
    await page.mouse.move(30, 180)
    await expect(side(page)).toHaveAttribute('data-expanded', 'true')
    for (const label of ['Dashboard', 'Sign Document', 'Verify Signature', 'Key Vault', 'Settings']) {
      await page.getByRole('link', { name: label, exact: true }).click()
      await expect(page.getByRole('link', { name: label, exact: true })).toHaveAttribute('aria-current', 'page')
      await expect(side(page)).toHaveAttribute('data-expanded', 'true')
      expect(await side(page).evaluate(node => node.matches(':hover'))).toBe(true)
    }
  }
  await page.getByRole('link', { name: 'Key Vault', exact: true }).click()
  await expect(page.locator('.vault-status-line')).toContainText('Unlocked')
  await page.getByRole('link', { name: 'Sign Document', exact: true }).click()
  await expect(page.locator('main')).toContainText('Research document with a longer filename.pdf')
  // The existing per-screen accordion starts at the vault step on remount;
  // selected document and authenticated provider state must still be ready.
  await expect(page.getByRole('button', { name: 'Continue to review', exact: true })).toBeEnabled()
  await page.getByRole('button', { name: 'Continue to review', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Review and sign step', exact: true })).toHaveAttribute('aria-expanded', 'true')
  await page.getByRole('link', { name: 'Verify Signature', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'HYBRID VALID', exact: true })).toBeVisible()
})

test('Auto cancels a pending leave on re-entry and closes at the fresh 220 ms boundary', async ({ page }) => {
  await start(page); await freeze(page)
  for (let cycle = 0; cycle < 3; cycle++) {
    await page.mouse.move(900, 180); await page.clock.runFor(150)
    await page.mouse.move(30, 180); await page.clock.runFor(300)
    await expect(side(page)).toHaveAttribute('data-expanded', 'true')
  }
  await page.mouse.move(900, 180); await page.clock.runFor(219)
  await expect(side(page)).toHaveAttribute('data-expanded', 'true')
  await page.clock.runFor(1)
  await expect(side(page)).toHaveAttribute('data-expanded', 'false')
})

test('unpinning inside enables Auto immediately and closes on leave without a manual collapse', async ({ page }) => {
  await start(page, 1440, 900); await freeze(page)
  await page.getByRole('button', { name: 'Pin sidebar', exact: true }).click()
  await expect(side(page)).toHaveAttribute('data-mode', 'pinned')
  await page.getByRole('button', { name: 'Unpin sidebar', exact: true }).click()
  await expect(auto(page)).toHaveAttribute('aria-pressed', 'true')
  await expect(side(page)).toHaveAttribute('data-expanded', 'true')
  await page.mouse.move(1000, 180); await page.clock.runFor(220)
  await expect(side(page)).toHaveAttribute('data-expanded', 'false')
  await page.mouse.move(30, 180); await page.clock.runFor(140)
  await expect(side(page)).toHaveAttribute('data-expanded', 'true')
})

test('unpinning or enabling Auto with the pointer outside arms collapse immediately', async ({ page }) => {
  await start(page, 1440, 900); await freeze(page)
  await page.getByRole('button', { name: 'Pin sidebar', exact: true }).click()
  await page.mouse.move(1000, 180)
  await page.getByRole('button', { name: 'Unpin sidebar', exact: true }).evaluate(node => (node as HTMLButtonElement).click())
  await page.clock.runFor(220)
  await expect(side(page)).toHaveAttribute('data-expanded', 'false')
  await page.mouse.move(30, 180); await page.clock.runFor(140)
  await auto(page).click() // Manual, expanded.
  await page.mouse.move(1000, 180); await page.clock.runFor(500)
  await expect(side(page)).toHaveAttribute('data-expanded', 'true')
  await auto(page).evaluate(node => (node as HTMLButtonElement).click())
  await page.clock.runFor(220)
  await expect(side(page)).toHaveAttribute('data-expanded', 'false')
})

test('mode switches cancel stale timers and Auto remains pointer-driven through live resizing', async ({ page }) => {
  await start(page, 1440, 900); await freeze(page)
  await page.mouse.move(1000, 180); await page.clock.runFor(100)
  await page.mouse.move(150, 100)
  await page.getByRole('button', { name: 'Pin sidebar', exact: true }).click()
  await page.clock.runFor(500)
  await expect(side(page)).toHaveAttribute('data-expanded', 'true')
  await page.getByRole('button', { name: 'Unpin sidebar', exact: true }).click()
  for (const [width, height] of sizes) {
    await page.mouse.move(width - 20, 180)
    await page.setViewportSize({ width, height }); await page.mouse.move(width - 20, 180)
    await page.clock.runFor(500)
    await expect(side(page)).toHaveAttribute('data-expanded', 'false')
    await page.mouse.move(30, 180); await page.clock.runFor(140)
    await expect(side(page)).toHaveAttribute('data-expanded', 'true')
  }
})

test('View full ID is a stationary button with stable copy controls and exact expandable text', async ({ page }, info) => {
  test.setTimeout(60000)
  await responsiveHost(page)
  await page.addInitScript(() => Object.defineProperty(navigator, 'clipboard', { configurable: true, value: {
    writeText: async (value: string) => { Object.assign(window, { __copiedId: value }) },
  } }))
  await go(page, 'verify')
  const id = page.getByRole('group', { name: 'Hybrid key ID', exact: true }).first()
  const toggle = id.getByRole('button', { name: 'View full ID', exact: true })
  const copy = id.getByRole('button', { name: 'Copy full ID', exact: true })
  for (const [width, height] of sizes) {
    await page.setViewportSize({ width, height })
    await id.scrollIntoViewIfNeeded()
    const before = { toggle: await toggle.boundingBox(), copy: await copy.boundingBox() }
    const down = await toggle.locator('svg').evaluate(node => getComputedStyle(node).transform)
    for (let repeat = 0; repeat < 3; repeat++) {
      await expect(toggle).toHaveAttribute('aria-expanded', 'false')
      const region = await toggle.getAttribute('aria-controls')
      expect(region).toBeTruthy()
      await toggle.focus(); await page.keyboard.press(repeat % 2 ? 'Space' : 'Enter')
      await expect(toggle).toHaveText('View full ID')
      await expect(toggle).toHaveAttribute('aria-expanded', 'true')
      await expect(page.locator(`[id="${region}"]`)).toBeVisible()
      await expect(id.locator('.key-id-full')).toHaveText(publicId)
      expect(await toggle.locator('svg').evaluate(node => getComputedStyle(node).transform)).not.toBe(down)
      expect({ toggle: await toggle.boundingBox(), copy: await copy.boundingBox() }).toEqual(before)
      await copy.click()
      expect(await page.evaluate(() => (window as unknown as { __copiedId: string }).__copiedId)).toBe(publicId)
      await toggle.click()
      await expect(toggle).toHaveAttribute('aria-expanded', 'false')
      await expect(toggle).toHaveText('View full ID')
      await expect(id.locator('.key-id-full')).not.toBeVisible()
      expect({ toggle: await toggle.boundingBox(), copy: await copy.boundingBox() }).toEqual(before)
    }
  }
  if (info.project.name === 'desktop-1366') {
    await mkdir('qa/phase4b3b1-interactions', { recursive: true })
    await page.screenshot({ path: 'qa/phase4b3b1-interactions/id-collapsed.png', animations: 'disabled' })
    await toggle.click()
    await page.screenshot({ path: 'qa/phase4b3b1-interactions/id-expanded.png', animations: 'disabled' })
  }
})

test('ID controls stay fixed when opening details first requires a vertical scrollbar', async ({ page }) => {
  await responsiveHost(page)
  await page.setViewportSize({ width: 1440, height: 900 }); await go(page, 'verify')
  const fit = await page.evaluate(() => {
    const content = document.querySelector('.page-container')!
    const bottom = Math.max(...[...content.children].map(node => node.getBoundingClientRect().bottom))
    return Math.ceil(bottom - content.getBoundingClientRect().top + parseFloat(getComputedStyle(content).paddingBottom)
      + document.querySelector('.topbar')!.getBoundingClientRect().height
      + document.querySelector('.task-actions-host')!.getBoundingClientRect().height + 1)
  })
  await page.setViewportSize({ width: 1440, height: fit })
  const toggle = page.getByRole('button', { name: 'View full ID', exact: true })
  const copy = page.getByRole('button', { name: 'Copy full ID', exact: true })
  expect(await page.locator('main').evaluate(node => node.scrollHeight <= node.clientHeight)).toBe(true)
  const before = { toggle: await toggle.boundingBox(), copy: await copy.boundingBox() }
  await toggle.click()
  await expect(toggle).toHaveAttribute('aria-expanded', 'true')
  expect(await page.locator('main').evaluate(node => node.scrollHeight > node.clientHeight)).toBe(true)
  expect({ toggle: await toggle.boundingBox(), copy: await copy.boundingBox() }).toEqual(before)
  await toggle.click()
  expect({ toggle: await toggle.boundingBox(), copy: await copy.boundingBox() }).toEqual(before)
})
