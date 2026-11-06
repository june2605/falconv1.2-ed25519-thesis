import { test, expect, type Page } from '@playwright/test'
import { go } from './helpers'

async function host(page: Page, fault = '') {
  await page.addInitScript(({ fault }) => {
    const calls: unknown[] = []
    const selection = { outcome: '', finish: null as null | (() => void) }
    const document = { documentId: 'd'.repeat(32), displayName: 'Original.pdf', sizeBytes: 700 }
    const vault = { vaultId: 'a'.repeat(32), sessionId: fault === 'locked' ? null : 'c'.repeat(32), displayName: 'Native vault',
      state: fault === 'locked' ? 'locked' : 'unlocked', hybridKeyId: 'hybrid-v1:' + 'b'.repeat(64),
      ed25519PublicKey: 'ab'.repeat(32), falconPublicKey: 'cd'.repeat(897), formatVersion: 1,
      algorithms: { ed25519: 'Ed25519', falcon512: 'Falcon-512' } }
    let job = { operationId: null as string | null, state: 'idle', document: null as typeof document | null,
      outputName: null as string | null, hybridKeyId: null as string | null, selfVerified: false, errorCode: null as string | null }
    const reply = (data: unknown) => ({ ok: true, protocolVersion: 1, data })
    Object.assign(window, { __signCalls: calls, __pdfSelection: selection, pywebview: { platform: 'edgechromium', api: {
      get_app_info: async () => reply({ applicationName: 'HybridSign', applicationVersion: '0.1.0', runtime: 'pywebview-edgechromium', desktopStatus: 'connected' }),
      get_capabilities: async () => reply({ nativeShell: true, vaultOperations: true, vaultCreate: true, vaultUnlock: true, vaultLock: true,
        vaultPasswordChange: false, vaultBackupRestore: false, pdfSigning: true, pdfVerification: false, accountRegistry: false }),
      get_vault_state: async () => reply({ vault, cancelled: false }),
      create_vault: async () => reply({ vault, cancelled: false }), unlock_vault: async () => reply({ vault, cancelled: false }),
      lock_vault: async () => reply({ vault, cancelled: false }),
      choose_pdf: async () => {
        if (selection.outcome === 'reject') return { ok: false, protocolVersion: 1, error: { code: 'PDF_INVALID', message: 'private native diagnostics' } }
        if (selection.outcome === 'malformed') return reply({ document: { documentId: 'invalid' }, cancelled: false })
        if (selection.outcome === 'pending') await new Promise<void>(resolve => { selection.finish = resolve })
        const cancelled = fault === 'cancel' || selection.outcome === 'cancel'
        return reply({ document: cancelled ? null : document, cancelled })
      },
      get_signing_state: async () => reply(job),
      sign_pdf: async (...args: string[]) => {
        calls.push(args)
        if (fault === 'preflight') return { ok: false, protocolVersion: 1, error: { code: 'STALE_SESSION', message: 'private native diagnostics' } }
        job = { operationId: args[3], state: 'running', document, outputName: null, hybridKeyId: vault.hybridKeyId, selfVerified: false, errorCode: null }
        setTimeout(() => { job = { ...job, state: fault === 'engine-failure' ? 'outcome-uncertain' : 'completed',
          outputName: fault === 'engine-failure' ? null : 'Original-signed.pdf', selfVerified: !['engine-failure', 'forged-completion'].includes(fault),
          errorCode: fault === 'engine-failure' ? 'SIGN_UNCERTAIN' : null } }, 700)
        if (fault === 'lost-response') throw new Error('private native transport diagnostic')
        return reply(job)
      },
    } } })
    window.dispatchEvent(new Event('pywebviewready'))
  }, { fault })
}

async function review(page: Page) {
  await page.getByRole('button', { name: 'Choose PDF', exact: true }).click()
  await page.getByRole('button', { name: 'Continue to review', exact: true }).click()
}

test('native signing uses the real workflow and reports only confirmed completion', async ({ page }) => {
  await host(page)
  await go(page, 'sign')
  await expect(page.getByRole('button', { name: 'Sign PDF', exact: true })).toBeDisabled()
  await expect(page.locator('input[type=file]')).toHaveCount(0)
  await review(page)
  await page.getByRole('button', { name: 'Sign PDF', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Sign PDF', exact: true })).toBeDisabled()
  await expect(page.getByRole('heading', { name: 'Signed PDF saved', exact: true })).toBeVisible()
  await expect(page.locator('main')).toContainText('Original-signed.pdf')
  await expect(page.locator('main')).toContainText('Completed self-verification')
  await expect(page.locator('main')).toContainText('hybrid-v1:' + 'b'.repeat(64))
  const calls = await page.evaluate(() => (window as unknown as { __signCalls: string[][] }).__signCalls)
  expect(calls).toHaveLength(1)
  expect(calls[0].slice(0, 3)).toEqual(['d'.repeat(32), 'a'.repeat(32), 'c'.repeat(32)])
  await page.getByRole('link', { name: 'Verify Signature', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Verify PDF', exact: true })).toBeDisabled()
  await expect(page.getByText('Explore example results')).toHaveCount(0)
})

test('lost submission response reconciles the same job without retrying', async ({ page }) => {
  await host(page, 'lost-response')
  await go(page, 'sign')
  await review(page)
  await page.getByRole('button', { name: 'Sign PDF', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Signed PDF saved', exact: true })).toBeVisible()
  await expect(page.locator('body')).not.toContainText('private native transport diagnostic')
  expect(await page.evaluate(() => (window as unknown as { __signCalls: unknown[] }).__signCalls.length)).toBe(1)
})

test('locked native vault cannot enable signing', async ({ page }) => {
  await host(page, 'locked')
  await go(page, 'sign')
  await page.getByRole('button', { name: 'Choose PDF', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Continue to review', exact: true })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Sign PDF', exact: true })).toBeDisabled()
})

test('cancelled native PDF chooser never selects a document', async ({ page }) => {
  await host(page, 'cancel')
  await go(page, 'sign')
  await page.getByRole('button', { name: 'Choose PDF', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Sign PDF', exact: true })).toBeDisabled()
  await expect(page.locator('main')).not.toContainText('Original.pdf')
})

test('uncertain publication is not displayed as success or automatically retried', async ({ page }) => {
  await host(page, 'engine-failure')
  await go(page, 'sign')
  await review(page)
  await page.getByRole('button', { name: 'Sign PDF', exact: true }).click()
  await expect(page.getByText('Signing outcome uncertain', { exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Signed PDF saved', exact: true })).toHaveCount(0)
  expect(await page.evaluate(() => (window as unknown as { __signCalls: unknown[] }).__signCalls.length)).toBe(1)
})

test('rapid duplicate clicks submit one operation and route changes preserve it', async ({ page }) => {
  await host(page)
  await go(page, 'sign')
  await review(page)
  await page.getByRole('button', { name: 'Sign PDF', exact: true }).evaluate(button => { (button as HTMLButtonElement).click(); (button as HTMLButtonElement).click() })
  await page.getByRole('link', { name: 'Key Vault', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Lock Vault', exact: true })).toBeDisabled()
  await page.getByRole('link', { name: 'Sign Document', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Signed PDF saved', exact: true })).toBeVisible()
  expect(await page.evaluate(() => (window as unknown as { __signCalls: unknown[] }).__signCalls.length)).toBe(1)
})

test('explicit preflight rejection remains recoverable without a false pending job', async ({ page }) => {
  await host(page, 'preflight')
  await go(page, 'sign')
  await review(page)
  await page.getByRole('button', { name: 'Sign PDF', exact: true }).click()
  await expect(page.locator('main')).toContainText('Unlock the native vault again before signing.')
  await expect(page.getByRole('button', { name: 'Sign PDF', exact: true })).toBeEnabled()
  await expect(page.locator('body')).not.toContainText('private native diagnostics')
  await expect(page.getByRole('heading', { name: 'Signed PDF saved', exact: true })).toHaveCount(0)
})

test('malformed completion without literal self-verification never shows success', async ({ page }) => {
  await host(page, 'forged-completion')
  await go(page, 'sign')
  await review(page)
  await page.getByRole('button', { name: 'Sign PDF', exact: true }).click()
  await expect(page.getByText('Signing outcome not confirmed', { exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Signed PDF saved', exact: true })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Sign PDF', exact: true })).toBeDisabled()
})

for (const outcome of ['reject', 'cancel', 'malformed', 'pending']) test(`new PDF selection ${outcome} clears the old signing-success display`, async ({ page }) => {
  await host(page); await go(page, 'sign'); await review(page)
  await page.getByRole('button', { name: 'Sign PDF', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Signed PDF saved', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Choose PDF step', exact: true }).click()
  await page.evaluate(outcome => { (window as unknown as { __pdfSelection: { outcome: string } }).__pdfSelection.outcome = outcome }, outcome)
  await page.getByRole('button', { name: 'Choose PDF', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Signed PDF saved', exact: true })).toHaveCount(0)
  await expect(page.locator('main')).not.toContainText('Original-signed.pdf')
  if (outcome === 'pending') {
    await expect(page.getByRole('button', { name: 'Sign PDF', exact: true })).toBeDisabled()
    await page.evaluate(() => (window as unknown as { __pdfSelection: { finish: () => void } }).__pdfSelection.finish())
  }
  if (outcome === 'reject' || outcome === 'malformed') await expect(page.getByRole('button', { name: 'Sign PDF', exact: true })).toBeDisabled()
  expect(await page.evaluate(() => (window as unknown as { __signCalls: unknown[] }).__signCalls.length)).toBe(1)
  await expect(page.locator('body')).not.toContainText('private native diagnostics')
})
