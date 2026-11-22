import { test, expect } from '@playwright/test'
import { go, sample, unlock, review } from './helpers'

type Fault = 'none' | 'protocol' | 'flags' | 'secret-field' | 'exception' | 'hang' | 'missing-method'
async function mockNative(page: import('@playwright/test').Page, fault: Fault = 'none', delayed = false) {
  await page.addInitScript(({ fault, delayed }) => {
    const info = { ok: true, protocolVersion: fault === 'protocol' ? 2 : 1, data: {
      applicationName: 'HybridSign', applicationVersion: '0.1.0', runtime: 'pywebview-edgechromium', desktopStatus: 'connected',
      ...(fault === 'secret-field' ? { privateKey: 'must-not-display' } : {}),
    } }
    const capabilities = { ok: true, protocolVersion: 1, data: { nativeShell: true, vaultOperations: false,
      pdfSigning: fault === 'flags', pdfVerification: false, accountRegistry: false } }
    const invoke = async (value: unknown) => {
      if (fault === 'exception') throw new Error('C:/private/password.key')
      if (fault === 'hang') await new Promise(() => {})
      return value
    }
    const install = () => {
      Object.assign(window, { pywebview: { platform: 'edgechromium', api: { get_app_info: () => invoke(info),
        ...(fault === 'missing-method' ? {} : { get_capabilities: () => invoke(capabilities) }) } } })
      window.dispatchEvent(new Event('pywebviewready'))
    }
    if (delayed) setTimeout(install, 150)
    else install()
  }, { fault, delayed })
}

test('browser preview remains available without a native host', async ({ page }) => {
  await go(page, 'dashboard')
  await expect(page.locator('.preview-indicator')).toHaveText('UI PREVIEW')
  await expect(page.locator('.sidebar-note')).toContainText('Browser preview')
  await expect(page.getByText('Desktop', { exact: true })).toHaveCount(0)
})

for (const delayed of [false, true]) {
  test(`native metadata handshake ${delayed ? 'waits for event' : 'handles already-ready API'}`, async ({ page }) => {
    await mockNative(page, 'none', delayed)
    await go(page, 'dashboard')
    await expect(page.locator('.preview-indicator')).toHaveText('Desktop')
    await expect(page.locator('.sidebar-note')).toContainText('PDF tools unavailable')
    for (const label of ['Sign Document', 'Verify Signature', 'Key Vault', 'Settings', 'Dashboard']) {
      await page.getByRole('navigation').getByRole('link', { name: label, exact: true }).click()
      await expect(page.locator('.preview-indicator')).toHaveText('Desktop')
    }
    await page.getByRole('link', { name: 'Key Vault', exact: true }).click(); await unlock(page)
    await page.getByRole('link', { name: 'Sign Document', exact: true }).click(); await sample(page); await review(page)
    await expect(page.getByRole('button', { name: 'Sign PDF', exact: true })).toBeDisabled()
    await page.getByRole('button', { name: 'Preview signing', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Signing workflow previewed' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Download preview summary', exact: true })).toBeDisabled()
    await page.getByRole('link', { name: 'Verify Signature', exact: true }).click()
    await expect(page.getByRole('button', { name: 'Verify PDF', exact: true })).toBeDisabled()
  })
}

for (const fault of ['protocol', 'flags', 'secret-field', 'exception', 'missing-method'] as const) {
  test(`native handshake rejects ${fault} and exposes no internal error`, async ({ page }) => {
    await mockNative(page, fault)
    await go(page, 'dashboard')
    await page.waitForTimeout(350)
    await expect(page.locator('.preview-indicator')).toHaveText('UI PREVIEW')
    await expect(page.locator('body')).not.toContainText('password.key')
    await expect(page.locator('body')).not.toContainText('must-not-display')
    await page.getByRole('link', { name: 'Sign Document', exact: true }).click()
    await expect(page.getByRole('button', { name: 'Continue to vault', exact: true })).toBeDisabled()
  })
}

test('hung native calls have a bounded initialization timeout', async ({ page }) => {
  await mockNative(page, 'hang')
  await go(page, 'dashboard')
  await page.waitForTimeout(3200)
  await expect(page.locator('.preview-indicator')).toHaveText('UI PREVIEW')
  await expect(page.locator('.sidebar-note')).toContainText('Browser preview')
})

test('presence of pywebview alone does not enable native status', async ({ page }) => {
  await page.addInitScript(() => { Object.assign(window, { pywebview: {} }); window.dispatchEvent(new Event('pywebviewready')) })
  await go(page, 'dashboard')
  await expect(page.locator('.preview-indicator')).toHaveText('UI PREVIEW')
})

test('malformed native host getters do not leak exceptions or crash the UI', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.addInitScript(() => { Object.defineProperty(window, 'pywebview', { get() { throw new Error('private-host-error') } }) })
  await go(page, 'dashboard')
  await expect(page.locator('.preview-indicator')).toHaveText('UI PREVIEW')
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  expect(errors).toEqual([])
})
