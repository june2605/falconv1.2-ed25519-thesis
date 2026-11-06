import { test, expect, type Page } from '@playwright/test'
import { mkdir } from 'node:fs/promises'
import { go } from './helpers'
import { responsiveHost } from './support/native-responsive-host'

const sidebar = (page: Page) => page.getByRole('complementary', { name: 'Workspace sidebar', exact: true })
const automatic = (page: Page) => page.getByRole('button', { name: 'Automatic sidebar', exact: true })
async function open(page: Page) {
  await responsiveHost(page)
  await page.setViewportSize({ width: 1100, height: 700 })
  await go(page, 'verify')
  await page.getByRole('button', { name: 'Expand sidebar', exact: true }).click()
  await expect.poll(() => page.locator('main').evaluate(node => node.getBoundingClientRect().left)).toBe(250)
}
async function freeze(page: Page) {
  await page.clock.install()
  await page.clock.pauseAt(new Date(Date.now() + 60000))
}

test('Auto has visible on and off states, an accessible pressed state and stable sizing', async ({ page }, info) => {
  await open(page)
  await expect(automatic(page)).toHaveText('Auto on')
  await expect(automatic(page)).toHaveAttribute('aria-pressed', 'true')
  const on = await automatic(page).boundingBox()
  const activeColor = await automatic(page).evaluate(node => getComputedStyle(node).backgroundColor)
  await automatic(page).click()
  await expect(automatic(page)).toHaveText('Auto off')
  await expect(automatic(page)).toHaveAttribute('aria-pressed', 'false')
  expect(await automatic(page).boundingBox()).toEqual(on)
  expect(await automatic(page).evaluate(node => getComputedStyle(node).backgroundColor)).not.toBe(activeColor)
  await expect(sidebar(page)).toHaveAttribute('data-expanded', 'true')
  if (info.project.name === 'desktop-1366') {
    await mkdir('qa/phase4b3b1-sidebar/auto', { recursive: true })
    await page.screenshot({ path: 'qa/phase4b3b1-sidebar/auto/off.png', animations: 'disabled' })
  }
  await automatic(page).click()
  await expect(automatic(page)).toHaveText('Auto on')
  await expect(automatic(page)).toHaveAttribute('aria-pressed', 'true')
  await expect(sidebar(page)).toHaveAttribute('data-expanded', 'true')
  if (info.project.name === 'desktop-1366') await page.screenshot({ path: 'qa/phase4b3b1-sidebar/auto/on.png', animations: 'disabled' })
})

test('enabling Auto stays expanded under the pointer and collapses only after its leave delay', async ({ page }) => {
  await open(page); await freeze(page)
  await automatic(page).click() // Manual mode.
  await automatic(page).click() // Enable Auto without closing the panel.
  await page.clock.runFor(800)
  await expect(sidebar(page)).toHaveAttribute('data-expanded', 'true')
  await expect(automatic(page)).toBeFocused()
  await page.mouse.move(900, 160)
  await page.clock.runFor(219)
  await expect(sidebar(page)).toHaveAttribute('data-expanded', 'true')
  await page.clock.runFor(1)
  await expect(sidebar(page)).toHaveAttribute('data-expanded', 'false')
  await page.mouse.move(30, 180)
  await page.clock.runFor(140)
  await expect(sidebar(page)).toHaveAttribute('data-expanded', 'true')
})

test('Auto off disables pointer automation while explicit controls remain usable', async ({ page }) => {
  await open(page); await freeze(page)
  await automatic(page).click()
  await page.mouse.move(900, 160); await page.clock.runFor(500)
  await expect(sidebar(page)).toHaveAttribute('data-expanded', 'true')
  await page.getByRole('button', { name: 'Collapse sidebar', exact: true }).click()
  await page.mouse.move(900, 160); await page.clock.runFor(500)
  await page.mouse.move(30, 180); await page.clock.runFor(500)
  await expect(sidebar(page)).toHaveAttribute('data-expanded', 'false')
  await page.getByRole('button', { name: 'Expand sidebar', exact: true }).click()
  await expect(sidebar(page)).toHaveAttribute('data-expanded', 'true')
  await expect(automatic(page)).toHaveText('Auto off')
})

test('keyboard Auto activation holds expansion until focus leaves or Escape is pressed', async ({ page }) => {
  await open(page); await freeze(page)
  await automatic(page).focus()
  await page.keyboard.press('Space')
  await expect(automatic(page)).toHaveAttribute('aria-pressed', 'false')
  await page.keyboard.press('Space')
  await expect(automatic(page)).toHaveAttribute('aria-pressed', 'true')
  await page.mouse.move(900, 160); await page.clock.runFor(500)
  await expect(sidebar(page)).toHaveAttribute('data-expanded', 'true')
  await expect(automatic(page)).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(sidebar(page)).toHaveAttribute('data-expanded', 'false')
  await expect(page.getByRole('button', { name: 'Expand sidebar', exact: true })).toBeFocused()
})
