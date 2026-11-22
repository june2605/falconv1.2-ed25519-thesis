import { test, expect, type Page, type Locator } from '@playwright/test'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'
import { go } from './helpers'
import { responsiveHost, publicId } from './support/native-responsive-host'
import AxeBuilder from '@axe-core/playwright'

const sizes = [ [960, 600], [1100, 700], [1177, 740], [1280, 800], [1366, 768], [1440, 900], [1920, 1080] ] as const
const routes = ['dashboard', 'sign', 'verify', 'vault', 'settings']
const qa = path.resolve('qa/phase4b3b1')

async function reachable(page: Page, element: Locator) {
  await element.scrollIntoViewIfNeeded()
  const result = await element.evaluate(node => {
    const r = node.getBoundingClientRect(), main = document.querySelector('main')!.getBoundingClientRect()
    const inFooter = !!node.closest('.task-actions-host'), nav = !!node.closest('nav')
    const top = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2)
    return { x: r.x, right: r.right, height: r.height, inside: r.top >= (inFooter || nav ? 0 : main.top) - 1
      && r.bottom <= (inFooter || nav ? innerHeight : main.bottom) + 1, clear: top === node || node.contains(top) }
  })
  expect(result.x).toBeGreaterThanOrEqual(-1)
  expect(result.right).toBeLessThanOrEqual(page.viewportSize()!.width + 1)
  expect(result.height).toBeGreaterThanOrEqual(32)
  expect(result.inside).toBe(true)
  expect(result.clear).toBe(true)
}

async function layout(page: Page) {
  const metrics = await page.evaluate(() => {
    const main = document.querySelector('main')!, content = document.querySelector('.page-container')!, footer = document.querySelector('.task-actions-host')!
    const m = main.getBoundingClientRect(), f = footer.getBoundingClientRect()
    const overflow = [...main.querySelectorAll<HTMLElement>('button,select,input,summary,.card,h1,h2,h3,p,dt,dd')].filter(node => {
      const r = node.getBoundingClientRect()
      return r.width && r.height && !node.classList.contains('sr-only')
        && (r.left < m.left - 1 || r.right > m.right + 1 || node.scrollWidth > node.clientWidth + 2)
    }).map(node => node.className || node.tagName)
    const grid = content.querySelector('.workflow-grid,.vault-grid,.settings-layout,.dashboard-actions')
    const columns = grid ? getComputedStyle(grid).gridTemplateColumns.split(' ').length : 0
    return { pageOverflow: document.documentElement.scrollWidth > innerWidth, overflow, columns,
      width: content.clientWidth - parseFloat(getComputedStyle(content).paddingLeft) - parseFloat(getComputedStyle(content).paddingRight),
      footerSafe: !footer.children.length || m.bottom <= f.top + 1, mainHeight: m.height,
      bodyScroll: document.body.scrollTop, scrollOwner: getComputedStyle(main).overflowY }
  })
  expect(metrics.pageOverflow).toBe(false)
  expect(metrics.overflow).toEqual([])
  expect(metrics.columns).toBe(metrics.width < 960 ? 1 : 2)
  expect(metrics.footerSafe).toBe(true)
  expect(metrics.mainHeight).toBeGreaterThan(300)
  expect(metrics.bodyScroll).toBe(0)
  expect(metrics.scrollOwner).toBe('auto')
  return metrics
}

for (const [width, height] of sizes) for (const theme of ['light', 'dark']) {
  test(`all native pages reflow at ${width}x${height} ${theme}`, async ({ page }, info) => {
    await responsiveHost(page)
    await page.setViewportSize({ width, height })
    await go(page, 'settings')
    await page.getByRole('radio', { name: new RegExp(theme, 'i') }).check()
    await expect(page.locator('.preview-indicator')).toHaveText('Desktop')
    for (const route of routes) {
      await page.getByRole('link', { name: { dashboard: 'Dashboard', sign: 'Sign Document', verify: 'Verify Signature', vault: 'Key Vault', settings: 'Settings' }[route], exact: true }).click()
      await expect(page.locator('h1')).toBeFocused()
      if (route === 'sign') {
        await page.getByRole('button', { name: 'Choose PDF', exact: true }).click()
        await page.getByRole('button', { name: 'Continue to review', exact: true }).click()
      }
      await layout(page)
      for (const button of await page.locator('main button:visible, main summary:visible, .task-actions button, nav a').all()) await reachable(page, button)
      if (route === 'verify') await expect(page.getByRole('heading', { name: 'HYBRID VALID', exact: true })).toBeVisible()
      if (info.project.name === 'desktop-1366') {
        await mkdir(qa, { recursive: true })
        await page.locator('main').evaluate(node => { node.scrollTop = 0 })
        await page.screenshot({ path: path.join(qa, `${width}x${height}-${theme}-${route}.png`), animations: 'disabled' })
      }
    }
  })
}

test('live resizing preserves focused controls, scroll ownership and route reset', async ({ page }) => {
  await responsiveHost(page)
  await go(page, 'verify')
  await expect(page.getByRole('heading', { name: 'HYBRID VALID', exact: true })).toBeVisible()
  const picker = page.getByRole('button', { name: 'Choose encrypted vault', exact: true })
  await picker.focus()
  for (const [width, height] of [...sizes].reverse().concat([...sizes])) {
    await page.setViewportSize({ width, height })
    await expect(picker).toBeFocused()
    await expect.poll(() => picker.evaluate(node => {
      const r = node.getBoundingClientRect(), main = document.querySelector('main')!.getBoundingClientRect()
      return r.top >= main.top - 1 && r.bottom <= main.bottom + 1
    })).toBe(true)
    await reachable(page, picker)
    await layout(page)
  }
  await page.getByRole('link', { name: 'Settings', exact: true }).click()
  expect(await page.locator('main').evaluate(node => node.scrollTop)).toBe(0)
  await page.getByRole('link', { name: 'Verify Signature', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'HYBRID VALID', exact: true })).toBeVisible()
  expect(await page.locator('main').evaluate(node => node.scrollTop)).toBe(0)
})

test('compact public ID supports keyboard disclosure, exact copy and clipboard failure', async ({ page }) => {
  await responsiveHost(page)
  await page.addInitScript(() => Object.defineProperty(navigator, 'clipboard', { configurable: true, value: {
    writeText: async (value: string) => { Object.assign(window, { __copiedId: value }) },
  } }))
  await page.setViewportSize({ width: 960, height: 600 })
  await go(page, 'verify')
  const id = page.locator('.hybrid-key-id').first()
  await expect(id.locator('.key-id-compact')).toHaveText('hybrid-v1:01234567…89abcdef')
  await expect(id.locator('.key-id-full')).not.toBeVisible()
  await id.getByRole('button', { name: 'Copy full ID', exact: true }).focus()
  await page.keyboard.press('Space')
  expect(await page.evaluate(() => (window as unknown as { __copiedId: string }).__copiedId)).toBe(publicId)
  const disclosure = id.getByRole('button', { name: 'View full ID', exact: true })
  await disclosure.focus(); await page.keyboard.press('Enter')
  await expect(id.locator('.key-id-full')).toBeVisible()
  await expect(id.locator('.key-id-full')).toHaveText(publicId)
  await expect(disclosure).toBeFocused()
  await page.evaluate(() => Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: async () => { throw new Error('clipboard denied') } } }))
  await id.getByRole('button', { name: 'Copy full ID', exact: true }).click()
  await expect(id).toContainText('Clipboard unavailable')
  await expect(id.locator('.key-id-full')).toBeVisible()
  await layout(page)
})

for (const state of ['invalid', 'failed']) test(`resizing preserves ${state} and authenticated-source meaning`, async ({ page }) => {
  await responsiveHost(page, state, 'vault-authenticated')
  await go(page, 'verify')
  const heading = state === 'invalid' ? 'HYBRID INVALID' : 'Verification could not complete'
  for (const [width, height] of sizes) {
    await page.setViewportSize({ width, height })
    await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible()
    await expect(page.getByText('Vault unlocked when selected', { exact: true })).toBeVisible()
    await expect(page.locator('main')).toContainText('Signer identity is not established')
    await layout(page)
  }
})

test('browser preview stays distinct throughout dynamic resizing on every route', async ({ page }) => {
  await go(page, 'dashboard')
  for (const [width, height] of sizes) {
    await page.setViewportSize({ width, height })
    for (const route of routes) {
      await page.getByRole('link', { name: { dashboard: 'Dashboard', sign: 'Sign Document', verify: 'Verify Signature', vault: 'Key Vault', settings: 'Settings' }[route], exact: true }).click()
      await expect(page.locator('.preview-indicator')).toHaveText('UI PREVIEW')
      await layout(page)
    }
  }
})

test('native result and ID disclosure retain accessible names and theme contrast', async ({ page }) => {
  await responsiveHost(page)
  for (const theme of ['light', 'dark']) {
    await go(page, 'settings')
    await page.getByRole('radio', { name: new RegExp(theme, 'i') }).check()
    await page.getByRole('link', { name: 'Verify Signature', exact: true }).click()
    for (const [width, height] of [sizes[0], sizes[6]]) {
      await page.setViewportSize({ width, height })
      await expect(page.getByRole('heading', { name: 'HYBRID VALID', exact: true })).toBeVisible()
      const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
      expect(result.violations).toEqual([])
    }
  }
})
