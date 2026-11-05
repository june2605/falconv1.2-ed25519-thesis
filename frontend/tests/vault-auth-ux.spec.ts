import { test, expect, type Page } from '@playwright/test'
import { go } from './helpers'

async function native(page: Page, confirmed = false, staleRetry = false, malformedProgress = false) {
  await page.addInitScript(({ confirmed, staleRetry, malformedProgress }) => {
    const original = { vaultId: 'a'.repeat(32), sessionId: null as string | null, displayName: 'Original vault', state: 'locked',
      hybridKeyId: 'hybrid-v1:' + 'b'.repeat(64), ed25519PublicKey: 'ab'.repeat(32), falconPublicKey: 'cd'.repeat(897),
      formatVersion: 1, algorithms: { ed25519: 'Ed25519', falcon512: 'Falcon-512' } }
    let vault: typeof original | null = confirmed ? { ...original } : null
    let selectionId: string | null = null, operation = 'idle'
    let finish: ((action: string) => void) | null = null
    const calls: unknown[] = []
    const reply = (data: unknown) => ({ ok: true, protocolVersion: 1, data })
    const state = (cancelled = false) => reply({ vault, selectionId, operation: malformedProgress ? [operation] : operation, cancelled })
    Object.assign(window, { __vaultCalls: calls, __finishVault: (action: string) => finish?.(action), pywebview: { platform: 'edgechromium', api: {
      get_app_info: async () => reply({ applicationName: 'HybridSign', applicationVersion: '0.1.0', runtime: 'pywebview-edgechromium', desktopStatus: 'connected' }),
      get_capabilities: async () => reply({ nativeShell: true, vaultOperations: true, vaultCreate: true, vaultUnlock: true, vaultLock: true,
        vaultPasswordChange: false, vaultBackupRestore: false, pdfSigning: false, pdfVerification: false, accountRegistry: false }),
      get_vault_state: async () => state(),
      create_vault: async () => { vault = { ...original }; return state() },
      lock_vault: async (...refs: string[]) => { calls.push(['lock', refs]); vault = { ...original }; return state() },
      unlock_vault: async (...refs: string[]) => {
        calls.push(['unlock', refs])
        if (refs.length && staleRetry) { selectionId = null; return { ok: false, protocolVersion: 1, error: { code: 'STALE_SELECTION', message: 'safe reselect required' } } }
        selectionId = 'd'.repeat(32)
        operation = 'waiting-password'
        const action = await new Promise<string>(resolve => { finish = resolve })
        finish = null
        if (action === 'cancel') { operation = 'idle'; return state(true) }
        operation = 'unlocking'
        await new Promise(resolve => setTimeout(resolve, 400))
        operation = 'idle'
        if (action === 'wrong') return { ok: false, protocolVersion: 1, error: { code: 'vault.unlock', message: 'raw internal detail must not display' } }
        vault = { ...original, state: 'unlocked', sessionId: 'c'.repeat(32) }
        selectionId = null
        return state()
      },
    } } })
    window.dispatchEvent(new Event('pywebviewready'))
  }, { confirmed, staleRetry, malformedProgress })
}

async function finish(page: Page, action: string) {
  await page.evaluate(value => (window as unknown as { __finishVault: (action: string) => void }).__finishVault(value), action)
}

async function failUnlock(page: Page) {
  await page.getByRole('button', { name: 'Unlock Vault', exact: true }).first().click()
  await expect(page.getByText('Waiting for password', { exact: true }).first()).toBeVisible()
  await finish(page, 'wrong')
  await expect(page.getByRole('alert')).toContainText("Couldn't unlock vault")
}

test('wrong password keeps bridge connected, no authenticated metadata, and offers contextual retry', async ({ page }) => {
  await native(page)
  await go(page, 'vault')
  await failUnlock(page)
  await expect(page.getByRole('alert')).toContainText('The password may be incorrect, or the vault could not be authenticated. Please try again.')
  await expect(page.locator('.preview-indicator')).toHaveText('Desktop Connected')
  await expect(page.locator('main')).toContainText('No vault unlocked')
  await expect(page.locator('main')).not.toContainText('Vault state unavailable')
  await expect(page.locator('main')).not.toContainText('Native vault connection is unavailable')
  await expect(page.locator('.vault-name')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Try Again', exact: true })).toBeEnabled()
  await expect(page.locator('.toast-region')).not.toContainText('Vault unlocked')
  await expect(page.locator('body')).not.toContainText('raw internal detail')
})

test('safe retry requests a new native password using only the opaque reference', async ({ page }) => {
  await native(page, true)
  await go(page, 'vault')
  await failUnlock(page)
  await expect(page.locator('.vault-name')).toHaveText('Original vault')
  await expect(page.locator('.vault-status-line')).toContainText('Locked')
  await page.getByRole('button', { name: 'Try Again', exact: true }).click()
  await expect(page.getByText('Waiting for password', { exact: true }).first()).toBeVisible()
  await finish(page, 'valid')
  await expect(page.getByText('Unlocking vault', { exact: true }).first()).toBeVisible()
  await expect(page.locator('.vault-status-line')).toContainText('Unlocked')
  await expect(page.locator('main')).toContainText('hybrid-v1:' + 'b'.repeat(64))
  await expect(page.getByRole('alert')).toHaveCount(0)
  const calls = await page.evaluate(() => (window as unknown as { __vaultCalls: unknown[] }).__vaultCalls)
  expect(calls).toEqual([['unlock', []], ['unlock', ['d'.repeat(32)]]])
  await expect(page.locator('input[type=password]')).toHaveCount(0)
})

test('new authentication attempt clears conflicting old success toasts', async ({ page }) => {
  await native(page, true)
  await go(page, 'vault')
  await page.getByRole('button', { name: 'Unlock Vault', exact: true }).first().click()
  await expect(page.getByText('Waiting for password', { exact: true }).first()).toBeVisible()
  await finish(page, 'valid')
  await expect(page.locator('.vault-status-line')).toContainText('Unlocked')
  await page.getByRole('button', { name: 'Lock Vault', exact: true }).click()
  await expect(page.locator('.toast-region')).toContainText('Vault locked')
  await failUnlock(page)
  await expect(page.locator('.toast-region')).not.toContainText('Vault locked')
  await expect(page.locator('.toast-region')).not.toContainText('Vault unlocked')
  await expect(page.getByRole('alert')).toHaveCount(1)
})

test('cancelled retry clears busy without an authentication error or success', async ({ page }) => {
  await native(page, true)
  await go(page, 'vault')
  await failUnlock(page)
  await page.getByRole('button', { name: 'Try Again', exact: true }).click()
  await expect(page.getByText('Waiting for password', { exact: true }).first()).toBeVisible()
  await finish(page, 'cancel')
  await expect(page.getByRole('alert')).toHaveCount(0)
  await expect(page.locator('.vault-status-line')).toContainText('Locked')
  await expect(page.getByRole('button', { name: 'Unlock Vault', exact: true }).first()).toBeEnabled()
  await expect(page.getByText('Waiting for password', { exact: true })).toHaveCount(0)
  await expect(page.locator('.toast-region')).not.toContainText('Vault unlocked')
})

test('authentication error is dismissible and focus refresh does not erase it', async ({ page }) => {
  await native(page)
  await go(page, 'vault')
  await failUnlock(page)
  await page.evaluate(() => window.dispatchEvent(new Event('focus')))
  await expect(page.getByRole('alert')).toContainText("Couldn't unlock vault")
  await page.getByRole('button', { name: 'Dismiss unlock error', exact: true }).click()
  await expect(page.getByRole('alert')).toHaveCount(0)
  await expect(page.locator('main')).toContainText('No vault unlocked')
})

test('a stale retry offers explicit safe reselection rather than using an obsolete reference', async ({ page }) => {
  await native(page, true, true)
  await go(page, 'vault')
  await failUnlock(page)
  await page.getByRole('button', { name: 'Try Again', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Select vault again', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Select vault again', exact: true }).click()
  await expect(page.getByText('Waiting for password', { exact: true }).first()).toBeVisible()
  await finish(page, 'cancel')
  await expect(page.getByRole('alert')).toHaveCount(0)
})

test('progress requires its exact string type and is never coerced from malformed data', async ({ page }) => {
  await native(page, false, false, true)
  await go(page, 'vault')
  await expect(page.getByRole('alert')).toContainText('Invalid native vault progress')
  await expect(page.locator('.vault-name')).toHaveCount(0)
})
