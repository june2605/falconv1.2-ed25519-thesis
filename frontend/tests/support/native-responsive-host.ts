import type { Page } from '@playwright/test'

export const publicId = 'hybrid-v1:' + '0123456789abcdef'.repeat(4)

/** Public-only contract double. No production bridge, filesystem or key changes. */
export async function responsiveHost(page: Page, result = 'valid', trust = 'unauthenticated-metadata', signing = 'idle') {
  await page.addInitScript(({ result, trust, publicId, signing }) => {
    const pdf = { documentId: 'd'.repeat(32), displayName: 'Research document with a longer filename.pdf', sizeBytes: 34004166 }
    const source = { keySourceId: 'e'.repeat(32), displayName: 'Local research vault', hybridKeyId: publicId, trust }
    const vault = { vaultId: 'a'.repeat(32), sessionId: 'c'.repeat(32), displayName: 'Local research vault', state: 'unlocked',
      hybridKeyId: publicId, ed25519PublicKey: 'ab'.repeat(32), falconPublicKey: 'cd'.repeat(897), formatVersion: 1,
      algorithms: { ed25519: 'Ed25519', falcon512: 'Falcon-512' } }
    const reply = (data: unknown) => ({ ok: true, protocolVersion: 1, data })
    const job = { operationId: 'f'.repeat(32), state: result, document: pdf, keySource: source,
      hybridValid: result === 'failed' ? null : result === 'valid', errorCode: result === 'failed' ? 'VERIFY_FAILED' : null }
    Object.assign(window, { __responsiveKeySource: source, pywebview: { platform: 'edgechromium', api: {
      get_app_info: async () => reply({ applicationName: 'HybridSign', applicationVersion: '0.1.0', runtime: 'pywebview-edgechromium', desktopStatus: 'connected' }),
      get_capabilities: async () => reply({ nativeShell: true, vaultOperations: true, vaultCreate: true, vaultUnlock: true, vaultLock: true,
        vaultPasswordChange: false, vaultBackupRestore: false, pdfSigning: true, pdfVerification: true, accountRegistry: false }),
      get_vault_state: async () => reply({ vault, cancelled: false }), create_vault: async () => reply({ vault, cancelled: false }),
      unlock_vault: async () => reply({ vault, cancelled: false }), lock_vault: async () => reply({ vault, cancelled: false }),
      choose_pdf: async () => reply({ document: pdf, cancelled: false }), sign_pdf: async () => { throw new Error('Not invoked by layout tests') },
      get_signing_state: async () => reply(signing === 'running'
        ? { operationId: '6'.repeat(32), state: 'running', document: pdf, outputName: null, hybridKeyId: publicId, selfVerified: false, errorCode: null }
        : { operationId: null, state: 'idle', document: null, outputName: null, hybridKeyId: null, selfVerified: false, errorCode: null }),
      choose_verification_pdf: async () => reply({ document: pdf, cancelled: false }),
      choose_verification_keys: async () => reply({ keySource: (window as unknown as { __responsiveKeySource: typeof source }).__responsiveKeySource, cancelled: false }),
      use_authenticated_vault_keys: async () => reply({ keySource: { ...source, trust: 'vault-authenticated' }, cancelled: false }),
      verify_pdf: async () => reply(job), get_verification_state: async () => reply(job),
    } } })
    window.dispatchEvent(new Event('pywebviewready'))
  }, { result, trust, publicId, signing })
}
