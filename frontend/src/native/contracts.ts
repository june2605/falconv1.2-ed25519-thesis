/** Future allowlisted pywebview boundary. Types only: no bridge is connected.
 * Password entry belongs to a native dialog; passwords/private keys must never
 * be arguments, responses, React state or browser storage. Opaque IDs refer to
 * a future dedicated Python worker, never a serialized Python vault handle.
 */
export interface NativeDocumentReference {
  documentId: string
  displayName: string
  sizeBytes: number
}

export interface NativePublicVault {
  vaultId: string
  displayName: string
  hybridKeyId: string
  state: 'locked' | 'unlocked'
}

export interface NativeVerificationReport {
  kind: 'native'
  ed25519: 'valid' | 'invalid' | 'not-checked' | 'error'
  falcon512: 'valid' | 'invalid' | 'not-checked' | 'error'
  identity: 'not-established'
  trustedSigningTime: 'not-available'
}

export interface NativeBridgeV1 {
  readonly protocolVersion: 1
  choosePdf(): Promise<NativeDocumentReference | null>
  chooseVault(): Promise<NativePublicVault | null>
  createVault(request: { displayName: string }): Promise<NativePublicVault>
  requestVaultUnlock(request: { vaultId: string }): Promise<{ sessionId: string }>
  lockVault(request: { sessionId: string }): Promise<void>
  requestPasswordChange(request: { vaultId: string }): Promise<void>
  requestEncryptedBackup(request: { vaultId: string }): Promise<void>
  requestEncryptedRestore(): Promise<NativePublicVault>
  signDocument(request: { sessionId: string; documentId: string }): Promise<{ outputDocumentId: string }>
  verifyDocument(request: { documentId: string; publicKeySelectionId: string }): Promise<NativeVerificationReport>
}

export class NativeUnavailableError extends Error {
  constructor() {
    super('Native operations are not connected in this UI preview.')
    this.name = 'NativeUnavailableError'
  }
}

export function requireNativeBridge(): never {
  // Deliberately no window.pywebview probing, eval, Python code or fallback.
  throw new NativeUnavailableError()
}
