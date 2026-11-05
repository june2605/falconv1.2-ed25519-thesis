export type PageId = 'dashboard' | 'sign' | 'verify' | 'vault' | 'settings'
export type Appearance = 'light' | 'dark' | 'system'
export type VaultDialog = 'create' | 'unlock' | 'password' | 'backup' | 'restore' | 'public' | 'clear' | 'about' | 'language'

export interface DocumentSelection {
  name: string
  size: number
  modifiedAt: number
  source: 'sample' | 'browser-selection'
}

export interface DemoVault {
  kind: 'ui-preview'
  id: string
  name: string
  state: 'locked' | 'unlocked'
  keyId: 'demo:ed25519-falcon512-preview'
}

export type VerificationScenario = 'both-valid' | 'altered' | 'ed25519-fails' | 'falcon-fails' | 'error'
export type ExampleCheck = 'example-pass' | 'example-fail' | 'not-run'

export interface SigningPreview {
  kind: 'ui-preview'
  cryptographyPerformed: false
  document: DocumentSelection
  suggestedOutputName: string
  createdAt: string
}

export interface VerificationPreview {
  kind: 'ui-preview'
  cryptographyPerformed: false
  scenario: VerificationScenario
  document: DocumentSelection
  ed25519: ExampleCheck
  falcon: ExampleCheck
  identity: 'not-established'
  signingTime: 'not-available'
}

export interface PreviewActivity {
  id: string
  title: string
  detail: string
  at: number
  type: 'sign' | 'verify' | 'vault'
}

export interface ToastMessage {
  id: number
  title: string
  detail?: string
  tone: 'info' | 'success' | 'error'
}
