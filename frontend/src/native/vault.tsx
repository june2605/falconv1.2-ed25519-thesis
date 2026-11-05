import { createContext, useCallback, useContext, useEffect, useRef, useState, type PropsWithChildren } from 'react'
import { exact, record, response, vaultApi } from './desktop'
import { useNativeSigning } from './signing'
import { useDesktopConnection } from './status'
import { useWorkspace } from '../state/workspace'

export interface PublicVault {
  vaultId: string
  sessionId: string | null
  displayName: string
  state: 'locked' | 'unlocked'
  hybridKeyId: string
  ed25519PublicKey: string
  falconPublicKey: string
  formatVersion: 1
  algorithms: { ed25519: 'Ed25519'; falcon512: 'Falcon-512' }
}
type Operation = 'get_vault_state' | 'create_vault' | 'unlock_vault' | 'lock_vault'
type Phase = 'idle' | 'reading-state' | 'selecting-file' | 'waiting-password' | 'unlocking' | 'creating' | 'locking'
interface VaultReply { vault: PublicVault | null; cancelled: boolean; selectionId: string | null; operation: Phase }
interface OperationError { code: string; title: string; message: string }
class VaultRequestError extends Error {
  constructor(message: string, readonly code = 'INVALID_RESPONSE') { super(message) }
}
const errors: Record<string, string> = {
  'vault.unlock': 'The password may be incorrect, or the vault could not be authenticated. Please try again.',
  'vault.exists': 'Destination already exists. Choose a new filename.',
  'vault.security': 'A fixed local NTFS drive and the approved Windows permissions are required.',
  'vault.path': 'Select a safe local vault path without links or aliases.',
  'vault.permission': 'Windows denied vault access. Permissions were not changed.',
  'vault.format': 'The selected file is not a supported encrypted vault.',
  'vault.profile': 'The selected vault profile is not supported.',
  'vault.conflict': 'Vault changed. Its session was locked; reopen it explicitly.',
  'vault.file_locked': 'Vault is in use by another operation. Retry explicitly.',
  'vault.io': 'Vault I/O failed. Inspect the selected location before retrying; publication or cleanup may have completed.',
  STALE_SESSION: 'Vault session is no longer valid. Refresh its status.',
  STALE_SELECTION: 'The selected vault is no longer available. Select it again.',
  VAULT_ACTIVE: 'Lock the current vault before opening or creating another.',
  BUSY: 'Another native operation is in progress.',
  TIMEOUT: 'Native operation timed out. Inspect the vault location before retrying.',
  UNAVAILABLE: 'Native vault connection is unavailable.',
}

function publicVault(value: unknown): value is PublicVault {
  if (!exact(value, ['vaultId', 'sessionId', 'displayName', 'state', 'hybridKeyId', 'ed25519PublicKey', 'falconPublicKey', 'formatVersion', 'algorithms'])) return false
  return typeof value.vaultId === 'string' && /^[0-9a-f]{32}$/.test(value.vaultId)
    && (value.state === 'locked' && value.sessionId === null || value.state === 'unlocked' && typeof value.sessionId === 'string' && /^[0-9a-f]{32}$/.test(value.sessionId))
    && typeof value.displayName === 'string' && value.displayName.length > 0 && Array.from(value.displayName).length <= 80 && !/[\x00-\x1f\x7f]/.test(value.displayName)
    && typeof value.hybridKeyId === 'string' && /^hybrid-v1:[0-9a-f]{64}$/.test(value.hybridKeyId)
    && typeof value.ed25519PublicKey === 'string' && /^[0-9a-f]{64}$/.test(value.ed25519PublicKey)
    && typeof value.falconPublicKey === 'string' && /^[0-9a-f]{1794}$/.test(value.falconPublicKey)
    && value.formatVersion === 1 && exact(value.algorithms, ['ed25519', 'falcon512'])
    && value.algorithms.ed25519 === 'Ed25519' && value.algorithms.falcon512 === 'Falcon-512'
}

async function request(operation: Operation, refs: string[] = []): Promise<VaultReply> {
  let reply: unknown
  let timer: number | undefined
  try {
    const host: unknown = (window as unknown as { pywebview?: unknown }).pywebview
    if (!record(host) || host.platform !== 'edgechromium' || !vaultApi(host.api) || typeof host.api[operation] !== 'function') throw new Error()
    const invoked = (host.api[operation] as (...args: string[]) => Promise<unknown>)(...refs)
    reply = operation === 'get_vault_state' ? await Promise.race([invoked, new Promise((_, reject) => {
      timer = window.setTimeout(() => reject(new Error()), 2000)
    })]) : await invoked
  } catch { throw new VaultRequestError('Native vault connection is unavailable. No success was confirmed.', 'UNAVAILABLE') }
  finally { if (timer !== undefined) window.clearTimeout(timer) }
  if (exact(reply, ['ok', 'protocolVersion', 'error']) && reply.ok === false && reply.protocolVersion === 1 && exact(reply.error, ['code', 'message'])) {
    const code = typeof reply.error.code === 'string' ? reply.error.code : 'INVALID_RESPONSE'
    throw new VaultRequestError(errors[code] ?? 'Native vault operation failed. No success was confirmed.', code)
  }
  const result = response(reply)
  const extended = exact(result, ['vault', 'cancelled', 'selectionId', 'operation'])
  if (!(exact(result, ['vault', 'cancelled']) || extended) || !result || typeof result.cancelled !== 'boolean' || !(result.vault === null || publicVault(result.vault))) throw new VaultRequestError('Invalid native vault response. No success was confirmed.')
  if (extended && (!(result.selectionId === null || typeof result.selectionId === 'string' && /^[0-9a-f]{32}$/.test(result.selectionId))
    || typeof result.operation !== 'string' || !['idle', 'reading-state', 'selecting-file', 'waiting-password', 'unlocking', 'creating', 'locking'].includes(result.operation))) throw new VaultRequestError('Invalid native vault progress. No success was confirmed.')
  if (!result.cancelled && (operation === 'create_vault' || operation === 'lock_vault') && (!result.vault || result.vault.state !== 'locked')
    || !result.cancelled && operation === 'unlock_vault' && (!result.vault || result.vault.state !== 'unlocked')) throw new VaultRequestError('Invalid native vault state. No success was confirmed.')
  return { selectionId: null, operation: 'idle', ...result } as unknown as VaultReply
}

interface VaultState {
  integrated: boolean
  vault: PublicVault | null
  busy: boolean
  known: boolean
  error: OperationError | null
  progress: string | null
  canRetry: boolean
  dismissError: () => void
  retry: () => Promise<void>
  create: () => Promise<void>
  unlock: () => Promise<void>
  lock: () => Promise<void>
  refresh: () => Promise<void>
}
const VaultContext = createContext<VaultState | null>(null)

export function NativeVaultProvider({ children }: PropsWithChildren) {
  const signingBusy = useNativeSigning().busy
  const connection = useDesktopConnection()
  const integrated = connection.mode === 'desktop' && connection.capabilities.vaultOperations
  const [vault, setVault] = useState<PublicVault | null>(null)
  const [busy, setBusy] = useState(false), [known, setKnown] = useState(false), [error, setError] = useState<OperationError | null>(null)
  const [selectionId, setSelectionId] = useState<string | null>(null)
  const [operation, setOperation] = useState<Operation | null>(null), [phase, setPhase] = useState<Phase>('idle')
  const running = useRef(false), mounted = useRef(false)
  const { notify, dismissToast, toasts } = useWorkspace()
  const toastSnapshot = useRef(toasts)
  toastSnapshot.current = toasts
  const run = useCallback(async (operation: Operation, refs: string[] = []) => {
    if (!integrated || running.current || signingBusy && operation !== 'get_vault_state') return
    running.current = true
    setBusy(true); setOperation(operation)
    setPhase(operation === 'unlock_vault' ? refs.length ? 'waiting-password' : 'selecting-file' : operation === 'create_vault' ? 'selecting-file' : operation === 'lock_vault' ? 'locking' : 'reading-state')
    if (operation !== 'get_vault_state') {
      setError(null)
      for (const toast of toastSnapshot.current) {
        if (toast.tone === 'success' && ['Vault created', 'Vault unlocked', 'Vault locked'].includes(toast.title)) dismissToast(toast.id)
      }
    }
    let stopped = false, polling = false
    const poll = async () => {
      if (stopped || polling) return
      polling = true
      try {
        const status = await request('get_vault_state')
        if (!stopped && mounted.current) { setPhase(status.operation); setSelectionId(status.selectionId) }
      } catch { /* Progress is advisory; the actual operation determines success. */ }
      finally { polling = false }
    }
    const interval = operation === 'create_vault' || operation === 'unlock_vault' ? window.setInterval(() => void poll(), 100) : undefined
    const stopPolling = () => { stopped = true; if (interval !== undefined) window.clearInterval(interval) }
    try {
      const result = await request(operation, refs)
      stopPolling()
      if (!mounted.current) return
      setSelectionId(result.selectionId)
      if (!result.cancelled) {
        setVault(result.vault); setKnown(true)
        if (operation !== 'get_vault_state') notify(operation === 'create_vault' ? 'Vault created' : operation === 'unlock_vault' ? 'Vault unlocked' : 'Vault locked', 'Confirmed by the local Python vault worker.', 'success')
      }
    } catch (failure) {
      stopPolling()  // Late progress must not replace a recovered retry reference.
      const authenticationFailed = operation === 'unlock_vault' && failure instanceof VaultRequestError && failure.code === 'vault.unlock'
      if (authenticationFailed) {
        // Failed authentication creates no session. Keep only previously
        // confirmed locked metadata, then recover an optional safe retry ID.
        if (mounted.current) { setVault(current => current?.state === 'locked' ? current : null); setKnown(true) }
        try {
          const safe = await request('get_vault_state')
          if (mounted.current && safe.vault?.state !== 'unlocked') { setVault(safe.vault); setSelectionId(safe.selectionId) }
        } catch { if (mounted.current) setSelectionId(null) }
      } else if (mounted.current) { setVault(null); setKnown(false); setSelectionId(null) }
      if (mounted.current) setError({ code: failure instanceof VaultRequestError ? failure.code : 'INVALID_RESPONSE',
        title: authenticationFailed ? "Couldn't unlock vault" : 'Vault operation not confirmed',
        message: failure instanceof VaultRequestError ? failure.message : 'Invalid native vault response. No success was confirmed.' })
    } finally {
      stopPolling()
      running.current = false
      if (mounted.current) { setBusy(false); setOperation(null); setPhase('idle') }
    }
  }, [integrated, notify, dismissToast, signingBusy])
  useEffect(() => {
    mounted.current = true
    if (integrated) void run('get_vault_state')
    const focus = () => { if (integrated) void run('get_vault_state') }
    window.addEventListener('focus', focus)
    return () => { mounted.current = false; window.removeEventListener('focus', focus) }
  }, [integrated, run])
  const progress = operation ? ({ 'waiting-password': 'Waiting for password', unlocking: 'Unlocking vault',
    creating: 'Creating vault', locking: 'Locking vault', 'selecting-file': 'Choose a vault in Windows',
    'reading-state': 'Reading native vault state…', idle: operation === 'unlock_vault' ? 'Unlocking vault' : 'Completing vault operation…' }[phase])
    : error?.code === 'vault.unlock' ? 'Unable to unlock' : vault?.state === 'unlocked' ? 'Vault unlocked' : null
  return <VaultContext.Provider value={{ integrated, vault, busy: busy || signingBusy, known, error, progress, canRetry: !!selectionId,
    dismissError: () => setError(null), retry: () => run('unlock_vault', selectionId ? [selectionId] : []),
    create: () => run('create_vault'), unlock: () => run('unlock_vault'),
    lock: () => vault?.sessionId ? run('lock_vault', [vault.vaultId, vault.sessionId]) : Promise.resolve(),
    refresh: () => run('get_vault_state') }}>{children}</VaultContext.Provider>
}

export function useNativeVault(): VaultState {
  const value = useContext(VaultContext)
  if (!value) throw new Error('Native vault provider is missing')
  return value
}
