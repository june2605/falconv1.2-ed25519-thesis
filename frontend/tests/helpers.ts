import { expect, type Page } from '@playwright/test'

export async function go(page: Page, route: string) {
  await page.goto(`/#/${route}`)
  await page.evaluate(() => document.fonts.ready)
}

export async function sample(page: Page) {
  await page.getByRole('button', { name: /Just exploring/ }).click()
}

export async function examples(page: Page) {
  await page.getByText('Explore example results', { exact: true }).click()
}

export async function review(page: Page) {
  await page.getByRole('button', { name: 'Continue to review', exact: true }).click()
}

export async function unlock(page: Page) {
  await page.getByRole('button', { name: 'Preview unlock', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByRole('button', { name: 'Preview unlocked state' }).click()
  await expect(dialog).not.toBeVisible()
}

/** Tiny synthetic fixture, generated in memory; no research datasets or secrets. */
export const pdf = { name: 'Example document.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF') }
