import { test, expect } from '@playwright/test'
import { go, sample, unlock, review } from './helpers'

async function host(page: import('@playwright/test').Page, fault = '') {
  await page.addInitScript(({ fault }) => {
    const calls: unknown[] = []
    let vault: Record<string, unknown> | null = null
    const publicVault = () => ({ vaultId: 'a'.repeat(32), sessionId: null as string | null,
      displayName: 'personal', state: 'locked', hybridKeyId: 'hybrid-v1:' + 'b'.repeat(64),
      ed25519PublicKey: 'ab'.repeat(32), falconPublicKey: 'cd'.repeat(897), formatVersion: 1,
      algorithms: { ed25519: 'Ed25519', falcon512: 'Falcon-512' } })
    const reply = (data: unknown) => ({ ok: true, protocolVersion: 1, data })
    const action = (name: string, ...args: unknown[]) => {
      calls.push([name, args])
      if (fault === name) return { ok: false, protocolVersion: 1, error: { code: 'vault.unlock', message: 'Unsafe raw internal error' } }
      if (fault === 'cancel') return reply({ vault, cancelled: true })
      if (name === 'create') vault = publicVault()
      if (name === 'create' && fault === 'unicode-name') vault = { ...vault, displayName: '🔐'.repeat(80) }
      if (name === 'unlock') vault = { ...publicVault(), state: 'unlocked', sessionId: 'c'.repeat(32) }
      if (name === 'lock') vault = { ...vault, state: 'locked', sessionId: null }
      if (fault === 'private-field') return reply({ vault: { ...publicVault(), privateKey: 'must-not-display' }, cancelled: false })
      if (fault === 'getter') return Object.defineProperty({ protocolVersion: 1, data: {} }, 'ok', { enumerable: true, get() { throw new Error('C:/private/password.key') } })
      return reply({ vault, cancelled: false })
    }
    Object.assign(window, { __nativeCalls: calls, pywebview: { platform: 'edgechromium', api: {
      get_app_info: async () => reply({ applicationName: 'HybridSign', applicationVersion: '0.1.0', runtime: 'pywebview-edgechromium', desktopStatus: 'connected' }),
      get_capabilities: async () => reply({ nativeShell: true, vaultOperations: true, vaultCreate: true, vaultUnlock: true, vaultLock: true,
        vaultPasswordChange: false, vaultBackupRestore: false, pdfSigning: false, pdfVerification: false, accountRegistry: false }),
      get_vault_state: async () => action('state'), create_vault: async () => action('create'),
      unlock_vault: async () => action('unlock'), lock_vault: async (...args: unknown[]) => action('lock', ...args),
    } } })
    window.dispatchEvent(new Event('pywebviewready'))
  }, { fault })
}

test('native vault starts empty and never presents the demo vault as real', async ({ page }) => {
  await host(page)
  await go(page, 'vault')
  await expect(page.locator('.preview-indicator')).toHaveText('Desktop')
  await expect(page.getByRole('button', { name: 'Create Vault', exact: true }).first()).toBeVisible()
  await expect(page.getByRole('button', { name: 'Unlock Vault', exact: true }).first()).toBeVisible()
  await expect(page.locator('main')).not.toContainText('DEMO VAULT')
  await expect(page.locator('main')).not.toContainText('demo:')
  await expect(page.locator('input[type=password]')).toHaveCount(0)
})

test('native create unlock lock updates real public state and dashboard', async ({ page }) => {
  await host(page)
  await go(page, 'vault')
  await page.getByRole('button', { name: 'Create Vault', exact: true }).first().click()
  await expect(page.locator('.vault-name')).toHaveText('personal')
  await expect(page.locator('.vault-status-line')).toContainText('Locked')
  await page.getByRole('button', { name: 'Unlock Vault', exact: true }).first().click()
  await expect(page.locator('.vault-status-line')).toContainText('Unlocked')
  await page.getByRole('button', { name: 'Public key details', exact: true }).click()
  await expect(page.getByRole('dialog')).toContainText('ab'.repeat(32))
  await expect(page.getByRole('dialog')).toContainText('cd'.repeat(897))
  await page.getByRole('button', { name: 'Close dialog' }).click()
  await page.getByRole('link', { name: 'Dashboard', exact: true }).click()
  await expect(page.locator('.vault-summary')).toContainText('personal')
  await expect(page.locator('.vault-summary')).toContainText('Unlocked')
  await expect(page.locator('.vault-summary')).not.toContainText('DEMO')
  await page.getByRole('link', { name: 'Key Vault', exact: true }).click()
  await page.getByRole('button', { name: 'Lock Vault', exact: true }).click()
  await expect(page.locator('.vault-status-line')).toContainText('Locked')
  await expect(page.getByRole('button', { name: 'Change password', exact: true })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Encrypted backup', exact: true })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Restore a vault', exact: true })).toBeDisabled()
  const calls = await page.evaluate(() => (window as unknown as { __nativeCalls: unknown[] }).__nativeCalls)
  expect(calls).toContainEqual(['lock', ['a'.repeat(32), 'c'.repeat(32)]])
  expect(JSON.stringify(calls)).not.toMatch(/password|private|\.hvault|C:/)
})

for (const operation of ['create', 'unlock']) {
  test(`native ${operation} failure has no false success or raw exception`, async ({ page }) => {
    await host(page, operation)
    await go(page, 'vault')
    await page.getByRole('button', { name: operation === 'create' ? 'Create Vault' : 'Unlock Vault', exact: true }).first().click()
    await expect(page.getByRole('alert')).toBeVisible()
    await expect(page.locator('body')).not.toContainText('Unsafe raw internal error')
    await expect(page.locator('.vault-name')).toHaveCount(0)
    await expect(page.locator('body')).not.toContainText('Vault unlocked successfully')
  })
}

test('cancelled native dialogs do not create a successful vault state', async ({ page }) => {
  await host(page, 'cancel')
  await go(page, 'vault')
  await page.getByRole('button', { name: 'Create Vault', exact: true }).first().click()
  await expect(page.locator('.vault-name')).toHaveCount(0)
  await expect(page.locator('body')).not.toContainText('Vault created')
  await expect(page.getByRole('alert')).toHaveCount(0)
})

for (const fault of ['private-field', 'getter']) test(`nonpublic or malformed native vault metadata fails closed: ${fault}`, async ({ page }) => {
  await host(page, fault)
  await go(page, 'vault')
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page.locator('body')).not.toContainText('must-not-display')
  await expect(page.locator('body')).not.toContainText('password.key')
  await expect(page.locator('.vault-name')).toHaveCount(0)
})

test('real vault capability never enables PDF signing or verification', async ({ page }) => {
  await host(page)
  await go(page, 'vault')
  await page.getByRole('button', { name: 'Unlock Vault', exact: true }).first().click()
  await expect(page.locator('.vault-status-line')).toContainText('Unlocked')
  await page.getByRole('link', { name: 'Sign Document', exact: true }).click()
  await sample(page)
  // Real unlocked state must not authorize even the separate signing rehearsal.
  await expect(page.getByRole('button', { name: 'Preview unlock', exact: true })).toBeVisible()
  await unlock(page)
  await review(page)
  await expect(page.getByRole('button', { name: 'Sign PDF', exact: true })).toBeDisabled()
  await page.getByRole('link', { name: 'Verify Signature', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Verify PDF', exact: true })).toBeDisabled()
})

test('failed native lock is never presented as confirmed locking', async ({ page }) => {
  await host(page, 'lock')
  await go(page, 'vault')
  await page.getByRole('button', { name: 'Unlock Vault', exact: true }).first().click()
  await expect(page.locator('.vault-status-line')).toContainText('Unlocked')
  await page.getByRole('button', { name: 'Lock Vault', exact: true }).click()
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page.locator('.vault-status-line')).toHaveCount(0)
  await expect(page.locator('.toast-region')).not.toContainText('Vault locked')
  await page.getByRole('link', { name: 'Dashboard', exact: true }).click()
  await expect(page.locator('.vault-summary')).toContainText('Unknown')
  await expect(page.locator('.vault-summary')).toContainText('Status not confirmed')
})

test('native public names use the same Unicode code-point bound as Python', async ({ page }) => {
  await host(page, 'unicode-name')
  await go(page, 'vault')
  await page.getByRole('button', { name: 'Create Vault', exact: true }).first().click()
  await expect(page.locator('.vault-name')).toHaveText('🔐'.repeat(80))
  await expect(page.getByRole('alert')).toHaveCount(0)
})
