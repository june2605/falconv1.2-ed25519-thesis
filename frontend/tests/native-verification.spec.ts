import { test, expect, type Page } from '@playwright/test'
import { go } from './helpers'

async function host(page: Page, fault = '') {
  await page.addInitScript(({ fault }) => {
    const calls: string[][] = []
    const document = { documentId: 'd'.repeat(32), displayName: 'Signed.pdf', sizeBytes: 900 }
    const keySource = { keySourceId: 'e'.repeat(32), displayName: 'Local vault', hybridKeyId: 'hybrid-v1:' + 'b'.repeat(64), trust: 'unauthenticated-metadata' }
    const vault = { vaultId: 'a'.repeat(32), sessionId: 'c'.repeat(32), displayName: 'Local vault', state: 'unlocked',
      hybridKeyId: keySource.hybridKeyId, ed25519PublicKey: 'ab'.repeat(32), falconPublicKey: 'cd'.repeat(897),
      formatVersion: 1, algorithms: { ed25519: 'Ed25519', falcon512: 'Falcon-512' } }
    const reply = (data: unknown) => ({ ok: true, protocolVersion: 1, data })
    let job = { operationId: null as string | null, state: 'idle', document: null as typeof document | null,
      keySource: null as typeof keySource | null, hybridValid: null as boolean | null, errorCode: null as string | null }
    const api = {
      get_app_info: async () => reply({ applicationName: 'HybridSign', applicationVersion: '0.1.0', runtime: 'pywebview-edgechromium', desktopStatus: 'connected' }),
      get_capabilities: async () => reply({ nativeShell: true, vaultOperations: true, vaultCreate: true, vaultUnlock: true, vaultLock: true,
        vaultPasswordChange: false, vaultBackupRestore: false, pdfSigning: true, pdfVerification: true, accountRegistry: false }),
      get_vault_state: async () => reply({ vault, cancelled: false }), create_vault: async () => reply({ vault, cancelled: false }),
      unlock_vault: async () => reply({ vault, cancelled: false }), lock_vault: async () => reply({ vault, cancelled: false }),
      choose_pdf: async () => reply({ document, cancelled: false }),
      get_signing_state: async () => reply({ operationId: null, state: 'idle', document: null, outputName: null, hybridKeyId: null, selfVerified: false, errorCode: null }),
      sign_pdf: async () => { throw new Error('not invoked') },
      choose_verification_pdf: async () => reply({ document: fault === 'cancel' ? null : document, cancelled: fault === 'cancel' }),
      choose_verification_keys: async () => reply({ keySource, cancelled: false }),
      use_authenticated_vault_keys: async () => reply({ keySource: { ...keySource, trust: 'vault-authenticated' }, cancelled: false }),
      get_verification_state: async () => reply(job),
      verify_pdf: async (...args: string[]) => {
        calls.push(args)
        job = { operationId: args[2], state: 'running', document, keySource, hybridValid: null, errorCode: null }
        setTimeout(() => { job = { ...job, state: fault === 'failed' ? 'failed' : fault === 'invalid' ? 'invalid' : 'valid',
          hybridValid: fault === 'failed' ? null : fault !== 'invalid', errorCode: fault === 'failed' ? 'VERIFY_FAILED' : null }
          if (fault === 'malformed') job = { ...job, hybridValid: null }
        }, 600)
        if (fault === 'lost-response') throw new Error('private path and native error')
        return reply(job)
      },
    }
    Object.assign(window, { pywebview: { platform: 'edgechromium', api }, __verificationCalls: calls })
    window.dispatchEvent(new Event('pywebviewready'))
  }, { fault })
}

async function select(page: Page) {
  await page.getByRole('button', { name: 'Choose signed PDF', exact: true }).click()
  await page.getByRole('button', { name: 'Choose encrypted vault', exact: true }).click()
}

test('native verification reports the overall result and untrusted key source only', async ({ page }) => {
  await host(page)
  await go(page, 'verify')
  await expect(page.getByRole('button', { name: 'Verify PDF', exact: true })).toBeDisabled()
  await expect(page.locator('input[type=file],input[type=password]')).toHaveCount(0)
  await expect(page.getByText('Explore example results')).toHaveCount(0)
  await select(page)
  await expect(page.locator('main')).toContainText('UNAUTHENTICATED')
  await page.getByRole('button', { name: 'Verify PDF', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'HYBRID VALID', exact: true })).toBeVisible()
  await expect(page.locator('main')).toContainText('Ed25519 + Falcon-512')
  await expect(page.locator('main')).toContainText('hybrid-v1:' + 'b'.repeat(64))
  await expect(page.locator('main')).not.toContainText('Ed25519: valid')
  expect(await page.evaluate(() => (window as unknown as { __verificationCalls: string[][] }).__verificationCalls[0].slice(0, 2)))
    .toEqual(['d'.repeat(32), 'e'.repeat(32)])
})

for (const fault of ['invalid', 'failed', 'lost-response', 'malformed']) test(`native verification handles ${fault} without inventing results`, async ({ page }) => {
  await host(page, fault)
  await go(page, 'verify')
  await select(page)
  await page.getByRole('button', { name: 'Verify PDF', exact: true }).click()
  if (fault === 'invalid') await expect(page.getByRole('heading', { name: 'HYBRID INVALID', exact: true })).toBeVisible()
  if (fault === 'failed') await expect(page.getByText('Verification could not complete', { exact: true })).toBeVisible()
  if (fault === 'lost-response') await expect(page.getByRole('heading', { name: 'HYBRID VALID', exact: true })).toBeVisible()
  if (fault === 'malformed') await expect(page.getByText('Verification status unconfirmed', { exact: true })).toBeVisible()
  if (fault !== 'lost-response') await expect(page.getByRole('heading', { name: 'HYBRID VALID', exact: true })).toHaveCount(0)
  await expect(page.locator('body')).not.toContainText('private path and native error')
  expect(await page.evaluate(() => (window as unknown as { __verificationCalls: unknown[] }).__verificationCalls.length)).toBe(1)
})

test('public source can come from an authenticated vault and cancelling PDF selection cannot validate', async ({ page }) => {
  await host(page, 'cancel')
  await go(page, 'verify')
  await page.getByRole('button', { name: 'Use unlocked vault keys', exact: true }).click()
  await expect(page.locator('main')).toContainText('Vault unlocked when selected')
  await page.getByRole('button', { name: 'Choose signed PDF', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Verify PDF', exact: true })).toBeDisabled()
  await expect(page.getByRole('heading', { name: 'HYBRID VALID', exact: true })).toHaveCount(0)
})

test('duplicate clicks launch one verification and block signing and vault changes', async ({ page }) => {
  await host(page)
  await go(page, 'verify')
  await select(page)
  await page.getByRole('button', { name: 'Verify PDF', exact: true }).evaluate(button => { (button as HTMLButtonElement).click(); (button as HTMLButtonElement).click() })
  await page.getByRole('link', { name: 'Key Vault', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Lock Vault', exact: true })).toBeDisabled()
  await page.getByRole('link', { name: 'Verify Signature', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'HYBRID VALID', exact: true })).toBeVisible()
  expect(await page.evaluate(() => (window as unknown as { __verificationCalls: unknown[] }).__verificationCalls.length)).toBe(1)
})
