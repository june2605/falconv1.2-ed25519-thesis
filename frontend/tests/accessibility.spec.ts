import AxeBuilder from '@axe-core/playwright'
import { test, expect } from '@playwright/test'
import { examples, go, review, sample, unlock } from './helpers'

// Audit settled theme colors, not transient colors partway through a CSS transition.
// Normal-motion loading/navigation behavior is covered by workspace.spec.ts.
test.use({ reducedMotion: 'reduce' })

for (const route of ['dashboard', 'sign', 'verify', 'vault', 'settings']) {
  test(`${route} has no detected WCAG A/AA violations in light and dark`, async ({ page }) => {
    await go(page, route)
    if (route === 'sign') { await sample(page); await unlock(page); await review(page) }
    if (route === 'verify') {
      await sample(page); await examples(page); await page.getByRole('button', { name: 'Preview verification', exact: true }).click()
      await expect(page.getByRole('heading', { name: 'Example: both layers pass' })).toBeVisible()
    }
    for (const theme of ['light', 'dark']) {
      // Scan theme tokens for every screen without changing that screen's state.
      await page.evaluate(value => { document.documentElement.dataset.theme = value }, theme)
      const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
      expect(results.violations.map(issue => ({ id: issue.id, nodes: issue.nodes.map(node => ({ target: node.target, reason: node.failureSummary })) }))).toEqual([])
    }
  })
}

test('keyboard navigation, modal focus trap, Escape and return focus work', async ({ page }) => {
  await go(page, 'vault')
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'Skip to content' })).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('main')).toBeFocused()
  const trigger = page.getByRole('button', { name: 'Preview unlock', exact: true })
  await trigger.focus(); await page.keyboard.press('Enter')
  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
  expect(results.violations.map(issue => ({ id: issue.id, nodes: issue.nodes.map(node => ({ target: node.target, reason: node.failureSummary })) }))).toEqual([])
  for (let index = 0; index < 9; index++) {
    await page.keyboard.press('Tab')
    expect(await dialog.evaluate(element => element.contains(document.activeElement))).toBe(true)
  }
  await page.keyboard.press('Escape')
  await expect(dialog).not.toBeVisible()
  await expect(trigger).toBeFocused()
  await page.getByRole('button', { name: 'Vault options' }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('menu')).toBeVisible()
  await page.keyboard.press('ArrowDown'); await page.keyboard.press('Escape')
  await expect(page.getByRole('button', { name: 'Vault options' })).toBeFocused()
})

test('five screens remain usable without horizontal overflow at narrower widths', async ({ page }) => {
  for (const width of [900, 768, 390]) {
    await page.setViewportSize({ width, height: 900 })
    for (const route of ['dashboard', 'sign', 'verify', 'vault', 'settings']) {
      await go(page, route)
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width)
      expect(await page.getByRole('main').evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true)
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
      await expect(page.getByRole('navigation')).toBeVisible()
    }
  }
})
