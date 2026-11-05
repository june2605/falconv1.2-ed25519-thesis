import type { DemoVault, DocumentSelection, SigningPreview, VerificationPreview, VerificationScenario } from '../models'

/** This service changes UI state only. It has no network, filesystem or crypto API. */
function pause(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) return reject(new DOMException('Preview cancelled', 'AbortError'))
    const timer = window.setTimeout(() => {
      signal?.removeEventListener('abort', abort)
      resolve()
    }, ms)
    function abort() {
      window.clearTimeout(timer)
      reject(new DOMException('Preview cancelled', 'AbortError'))
    }
    signal?.addEventListener('abort', abort, { once: true })
  })
}

export const sampleDocument: DocumentSelection = {
  name: 'Service agreement.pdf', size: 248_320, modifiedAt: 0, source: 'sample',
}

export function initialDemoVault(): DemoVault {
  return { kind: 'ui-preview', id: 'demo-personal-vault', name: 'Personal signing vault', state: 'locked', keyId: 'demo:ed25519-falcon512-preview' }
}

export const demoService = {
  async vaultAction(name: string, signal?: AbortSignal): Promise<void> {
    if (!name.trim()) throw new Error('Enter a name for your demo vault.')
    await pause(450, signal)
  },
  async sign(document: DocumentSelection, vault: DemoVault, signal?: AbortSignal): Promise<SigningPreview> {
    if (vault.state !== 'unlocked') throw new Error('Preview an unlocked vault before continuing.')
    await pause(950, signal)
    return { kind: 'ui-preview', cryptographyPerformed: false, document,
      suggestedOutputName: document.name.replace(/\.pdf$/i, '') + '.signed.pdf', createdAt: new Date().toISOString() }
  },
  async verify(document: DocumentSelection, scenario: VerificationScenario, signal?: AbortSignal): Promise<VerificationPreview> {
    await pause(850, signal)
    const error = scenario === 'error'
    return { kind: 'ui-preview', cryptographyPerformed: false, document, scenario,
      ed25519: error ? 'not-run' : ['altered', 'ed25519-fails'].includes(scenario) ? 'example-fail' : 'example-pass',
      falcon: error ? 'not-run' : ['altered', 'falcon-fails'].includes(scenario) ? 'example-fail' : 'example-pass',
      identity: 'not-established', signingTime: 'not-available' }
  },
}

export async function selectPdf(file: File): Promise<DocumentSelection> {
  if (!file.name.toLowerCase().endsWith('.pdf')) throw new Error('Choose a PDF document with a .pdf extension.')
  if (file.size === 0) throw new Error('This file is empty. Choose a nonempty PDF document.')
  if (file.size > 50 * 1024 * 1024) throw new Error('This UI preview accepts PDFs up to 50 MB.')
  if (await file.slice(0, 5).text() !== '%PDF-') throw new Error('This file does not start with a PDF header.')
  return { name: file.name, size: file.size, modifiedAt: file.lastModified, source: 'browser-selection' }
}

export function downloadPreviewSummary(value: SigningPreview | VerificationPreview): void {
  const summary = { ...value, notice: 'UI PREVIEW ONLY. Not a signed PDF, cryptographic verification report, vault or backup.', nativeBridgeConnected: false }
  const url = URL.createObjectURL(new Blob([JSON.stringify(summary, null, 2)], { type: 'application/json' }))
  const link = document.createElement('a')
  link.href = url
  link.download = 'hybridsign-ui-preview.json'
  link.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 1_000)
}
