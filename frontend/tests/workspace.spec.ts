import { test, expect } from '@playwright/test'
import { readFile } from 'node:fs/promises'
import { examples, go, pdf, review, sample, unlock } from './helpers'

test('all navigation routes, history and focus work', async ({ page }) => {
  await go(page, 'dashboard')
  const entries = [['Sign Document', 'Sign a document'], ['Verify Signature', 'Verify a signature'], ['Key Vault', 'Manage your signing keys'], ['Settings', 'Personalize your workspace'], ['Dashboard', 'Your digital signing workspace']]
  for (const [label, heading] of entries) {
    await page.getByRole('navigation').getByRole('link', { name: label, exact: true }).click()
    await expect(page.getByRole('heading', { level: 1, name: heading })).toBeFocused()
    await expect(page.getByRole('navigation').getByRole('link', { name: label, exact: true })).toHaveAttribute('aria-current', 'page')
  }
  await page.goBack()
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Personalize your workspace')
  await go(page, 'unknown-route')
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Your digital signing workspace')
})

test('dashboard starts empty and primary actions are above the fold', async ({ page }) => {
  await go(page, 'dashboard')
  await expect(page.getByText('A fresh start for your documents')).toBeVisible()
  await expect(page.locator('.activity-list')).toHaveCount(0)
  await expect(page.locator('.action-sign')).toContainText('demo signing workflow')
  await expect(page.locator('.vault-summary')).toContainText('no keys loaded')
  expect(await page.getByRole('main').evaluate(element => element.scrollHeight)).toBeLessThanOrEqual(await page.getByRole('main').evaluate(element => element.clientHeight))
  for (const selector of ['.action-sign', '.action-verify']) {
    const box = await page.locator(selector).boundingBox()
    expect(box).not.toBeNull()
    expect(box!.y + box!.height).toBeLessThan(page.viewportSize()!.height)
  }
  await page.locator('.action-sign').click()
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Sign a document')
  await page.getByRole('link', { name: 'Dashboard', exact: true }).click()
  await page.locator('.action-verify').click()
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Verify a signature')
})

for (const invalid of [
  { name: 'notes.txt', text: '%PDF-1.7', message: 'Choose a PDF document with a .pdf extension.' },
  { name: 'empty.pdf', text: '', message: 'This file is empty. Choose a nonempty PDF document.' },
  { name: 'renamed.pdf', text: 'not a PDF', message: 'This file does not start with a PDF header.' },
]) {
  test(`PDF validation rejects ${invalid.name}`, async ({ page }) => {
    await go(page, 'sign')
    await page.getByLabel('Choose PDF document', { exact: true }).setInputFiles({ name: invalid.name, mimeType: 'application/pdf', buffer: Buffer.from(invalid.text) })
    await expect(page.getByRole('alert')).toHaveText(invalid.message)
    await expect(page.getByRole('button', { name: 'Continue to vault', exact: true })).toBeDisabled()
  })
}

test('PDF size limit is enforced before reading the header', async ({ page }) => {
  await go(page, 'sign')
  // Playwright's buffer upload itself has a 50 MB limit; create the File in-browser.
  const transfer = await page.evaluateHandle(() => {
    const data = new DataTransfer()
    data.items.add(new File([new Uint8Array(50 * 1024 * 1024 + 1)], 'large.pdf', { type: 'application/pdf' }))
    return data
  })
  await page.locator('.dropzone').dispatchEvent('drop', { dataTransfer: transfer })
  await expect(page.getByRole('alert')).toHaveText('This UI preview accepts PDFs up to 50 MB.')
})

test('local selection keeps metadata, supports removal and an honest preview', async ({ page }) => {
  await go(page, 'sign')
  await page.getByLabel('Choose PDF document', { exact: true }).setInputFiles(pdf)
  await expect(page.locator('.selected-document')).toContainText(pdf.name)
  await expect(page.locator('.selected-document')).toContainText('Selected locally')
  expect(await page.getByLabel('Choose PDF document', { exact: true }).evaluate((input: HTMLInputElement) => input.files?.length)).toBe(0)
  await page.getByRole('button', { name: 'Expand preview layout' }).click()
  await expect(page.getByRole('dialog')).toContainText('not a rendering of your PDF')
  await page.keyboard.press('Escape')
  await expect(page.getByRole('button', { name: 'Expand preview layout' })).toBeFocused()
  await page.getByRole('button', { name: 'Choose PDF step', exact: true }).click()
  await page.getByRole('button', { name: 'Remove selected document' }).click()
  await expect(page.getByRole('button', { name: 'Choose PDF', exact: true })).toBeVisible()
})

test('dropzone accepts a PDF and rejects multiple files', async ({ page }) => {
  await go(page, 'verify')
  const data = await page.evaluateHandle(() => {
    const transfer = new DataTransfer()
    transfer.items.add(new File(['%PDF-1.4\n%%EOF'], 'Dropped.pdf', { type: 'application/pdf' }))
    return transfer
  })
  await page.locator('.dropzone').dispatchEvent('drop', { dataTransfer: data })
  await expect(page.locator('.selected-document')).toContainText('Dropped.pdf')
  await page.getByRole('button', { name: 'Remove selected document' }).click()
  const multiple = await page.evaluateHandle(() => {
    const transfer = new DataTransfer()
    transfer.items.add(new File(['%PDF-1.4'], 'One.pdf'))
    transfer.items.add(new File(['%PDF-1.4'], 'Two.pdf'))
    return transfer
  })
  await page.locator('.dropzone').dispatchEvent('drop', { dataTransfer: multiple })
  await expect(page.getByRole('alert')).toHaveText('Choose one PDF document at a time.')
})

test('signing preview has prerequisites, loading, honest success and JSON-only download', async ({ page }) => {
  await go(page, 'sign')
  const submit = page.getByRole('button', { name: 'Preview signing', exact: true })
  await expect(page.getByRole('button', { name: 'Continue to vault', exact: true })).toBeDisabled()
  await expect(submit).not.toBeVisible()
  await sample(page); await expect(submit).not.toBeVisible()
  await unlock(page); await review(page); await expect(submit).toBeEnabled()
  await expect(page.getByRole('button', { name: 'Sign PDF', exact: true })).toBeDisabled()
  await submit.click()
  await expect(page.getByRole('button', { name: 'Previewing workflow…' })).toBeDisabled()
  await expect(page.getByRole('heading', { name: 'Signing workflow previewed' })).toBeVisible()
  await expect(page.locator('.result-area')).toContainText('No PDF was signed or changed.')
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Download preview summary' }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toBe('hybridsign-ui-preview.json')
  const body = JSON.parse(await readFile((await download.path())!, 'utf8'))
  expect(body.cryptographyPerformed).toBe(false)
  expect(body.nativeBridgeConnected).toBe(false)
  expect(body.kind).toBe('ui-preview')
  expect(body.notice).toContain('Not a signed PDF')
  await page.getByRole('link', { name: 'Dashboard', exact: true }).click()
  await expect(page.locator('.activity-list')).toContainText('Signing workflow previewed')
  await page.getByRole('button', { name: 'Clear activity', exact: true }).click()
  await expect(page.getByText('A fresh start for your documents')).toBeVisible()
})

test('leaving a loading preview cancels its completion', async ({ page }) => {
  await go(page, 'verify'); await sample(page); await examples(page)
  await page.getByRole('button', { name: 'Preview verification', exact: true }).click()
  await page.getByRole('link', { name: 'Dashboard', exact: true }).click()
  await page.waitForTimeout(1000)
  await expect(page.locator('.activity-list')).toHaveCount(0)
})

test('native unlock stays unavailable and never asks for a password', async ({ page }) => {
  await go(page, 'vault')
  await page.getByRole('button', { name: 'Preview unlock', exact: true }).click()
  await expect(page.getByRole('dialog')).toContainText('This preview never asks for your vault password.')
  await page.getByRole('button', { name: 'Request native unlock', exact: true }).click()
  await expect(page.getByRole('status')).toContainText('Native connection unavailable')
  await expect(page.locator('input[type="password"]')).toHaveCount(0)
  await page.keyboard.press('Escape')
  await expect(page.locator('.vault-status-line')).toContainText('Locked')
})

test('vault unlock, lock, menu, clear and validated create flows work', async ({ page }) => {
  await go(page, 'vault'); await unlock(page)
  await page.getByRole('button', { name: 'Lock demo vault', exact: true }).click()
  await expect(page.locator('.vault-status-line')).toContainText('Locked')
  await page.getByRole('button', { name: 'Vault options' }).click()
  await page.getByRole('menuitem', { name: 'Clear demo vault from view' }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Clear demo vault', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'A home for your signing keys' })).toBeVisible()
  await page.locator('.page-actions').getByRole('button', { name: 'Create demo vault', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByRole('button', { name: 'Create demo vault', exact: true }).click()
  await expect(page.getByLabel('Demo vault name')).toHaveAttribute('aria-invalid', 'true')
  await expect(dialog).toContainText('Use 3–40 characters without control characters.')
  await page.getByLabel('Demo vault name').fill('Research laptop')
  await page.getByLabel('Demo vault name').press('Enter')
  await expect(dialog).not.toBeVisible()
  await expect(page.locator('.vault-name')).toHaveText('Research laptop')
  await page.reload()
  await expect(page.locator('.vault-name')).toHaveText('Personal signing vault')
})

test('public details show only demo metadata and explicitly deny trusted identity', async ({ page }) => {
  await go(page, 'vault')
  await page.getByRole('button', { name: 'Public key details', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toContainText('demo:ed25519-falcon512-preview')
  await expect(dialog).toContainText('Not loaded in this UI preview')
  await expect(dialog).toContainText('Not established')
  await expect(dialog.locator('input, textarea')).toHaveCount(0)
})

for (const action of ['Change password', 'Encrypted backup', 'Restore a vault']) {
  test(`${action} has an honest native boundary and a labelled demo completion`, async ({ page }) => {
    await go(page, 'vault')
    const downloads: string[] = []
    page.on('download', item => downloads.push(item.suggestedFilename()))
    await page.getByRole('button', { name: action, exact: true }).click()
    await expect(page.getByRole('dialog')).toContainText('UI PREVIEW')
    await expect(page.getByRole('dialog').locator('input[type="password"]')).toHaveCount(0)
    await page.getByRole('button', { name: /^Request native / }).click()
    await expect(page.getByRole('status')).toContainText('Native connection unavailable')
    await page.getByRole('dialog').getByRole('button', { name: /^Preview (completion|restored state)$/ }).click()
    await expect(page.getByRole('dialog')).not.toBeVisible()
    await expect(page.getByRole('status')).toContainText('previewed')
    expect(downloads).toEqual([])
  })
}

const resultCases = [
  { value: 'both-valid', heading: 'Example: both layers pass', ed: 'pass', falcon: 'pass' },
  { value: 'altered', heading: 'Example: signature rejected', ed: 'fail', falcon: 'fail' },
  { value: 'ed25519-fails', heading: 'Example: signature rejected', ed: 'fail', falcon: 'pass' },
  { value: 'falcon-fails', heading: 'Example: signature rejected', ed: 'pass', falcon: 'fail' },
  { value: 'error', heading: 'Example: unable to verify', ed: 'not run', falcon: 'not run' },
]
for (const result of resultCases) {
  test(`verification scenario ${result.value} keeps layers and identity separate`, async ({ page }) => {
    await go(page, 'verify'); await sample(page); await examples(page)
    await page.getByLabel('Example scenario').selectOption(result.value)
    await page.getByRole('button', { name: 'Preview verification', exact: true }).click()
    await expect(page.getByRole('button', { name: 'Loading example…' })).toBeDisabled()
    await expect(page.getByRole('heading', { name: result.heading })).toBeVisible()
    await expect(page.locator('.verification-layer').nth(0)).toContainText(`Example: ${result.ed}`)
    await expect(page.locator('.verification-layer').nth(1)).toContainText(`Example: ${result.falcon}`)
    await expect(page.locator('.identity-note')).toContainText('Signer identity is not established')
    await page.getByText('Result details', { exact: true }).click()
    await expect(page.locator('.detail-panel')).toContainText('No CMS or PAdES claim')
    await expect(page.locator('.detail-panel')).toContainText('Not available')
  })
}

test('public file selection requires both filenames and never reads key bytes', async ({ page }) => {
  await go(page, 'verify'); await sample(page); await examples(page)
  await page.getByLabel('Public-key source').selectOption('files')
  await expect(page.getByRole('button', { name: 'Preview verification', exact: true })).toBeDisabled()
  // These synthetic non-key bytes deliberately prove this is a metadata placeholder.
  await page.getByLabel('Ed25519 public key', { exact: true }).setInputFiles({ name: 'ed-public.bin', mimeType: 'application/octet-stream', buffer: Buffer.from('UI metadata only') })
  await expect(page.getByRole('button', { name: 'Preview verification', exact: true })).toBeDisabled()
  await page.getByLabel('Falcon-512 public key', { exact: true }).setInputFiles({ name: 'falcon-public.bin', mimeType: 'application/octet-stream', buffer: Buffer.from('UI metadata only') })
  await expect(page.getByRole('button', { name: 'Preview verification', exact: true })).toBeEnabled()
  await expect(page.getByText('ed-public.bin', { exact: true })).toBeVisible()
})

test('appearance, system preference, reduced motion, language and reset work', async ({ page }) => {
  await go(page, 'settings')
  const limitations = page.locator('.about-limitations')
  const disclosure = limitations.locator('summary')
  await expect(disclosure.locator('svg')).toBeVisible()
  await expect(limitations.getByText('Native cryptography is not connected.')).not.toBeVisible()
  await disclosure.focus(); await page.keyboard.press('Enter')
  await expect(limitations).toHaveAttribute('open', '')
  await expect(limitations.getByText('Native cryptography is not connected.')).toBeVisible()
  await page.keyboard.press('Space')
  await expect(limitations).not.toHaveAttribute('open', '')
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
  await page.getByRole('radio', { name: 'Dark', exact: true }).check()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.getByRole('radio', { name: 'System', exact: true }).check()
  await page.emulateMedia({ colorScheme: 'light' })
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
  await page.emulateMedia({ colorScheme: 'dark' })
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.getByRole('switch', { name: 'Reduce motion' }).click()
  await expect(page.getByRole('switch', { name: 'Reduce motion' })).toHaveAttribute('aria-checked', 'true')
  await expect(page.locator('html')).toHaveClass('reduce-motion')
  await page.getByRole('button', { name: 'English', exact: true }).click()
  await expect(page.getByRole('dialog')).toContainText('Additional translations are not included')
  await page.keyboard.press('Escape')
  await page.getByRole('button', { name: 'Reset preview', exact: true }).click()
  await expect(page.getByRole('status')).toContainText('UI preview reset')
})

test('UI keeps state out of browser storage, uses local assets and has no runtime errors', async ({ page }) => {
  const errors: string[] = [], remoteRequests: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()) })
  page.on('request', request => { if (!request.url().startsWith('http://127.0.0.1:4173/') && !request.url().startsWith('blob:')) remoteRequests.push(request.url()) })
  await go(page, 'vault'); await unlock(page)
  await page.getByRole('link', { name: 'Sign Document', exact: true }).click()
  await sample(page); await review(page)
  await page.getByRole('button', { name: 'Preview signing', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Signing workflow previewed' })).toBeVisible()
  expect(await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length, bridge: 'pywebview' in window }))).toEqual({ local: 0, session: 0, bridge: false })
  await expect(page.locator('input[type="password"]')).toHaveCount(0)
  expect(errors).toEqual([])
  expect(remoteRequests).toEqual([])
})
