import { createContext, useContext, useEffect, useRef, useState, type PropsWithChildren } from 'react'
import { exact, record, response, verificationMethods } from './desktop'
import { useDesktopConnection } from './status'

interface Document { documentId: string; displayName: string; sizeBytes: number }
interface KeySource { keySourceId: string; displayName: string; hybridKeyId: string; trust: 'vault-authenticated' | 'unauthenticated-metadata' }
interface Job {
  operationId: string | null; state: 'idle' | 'ready' | 'queued' | 'running' | 'valid' | 'invalid' | 'failed'
  document: Document | null; keySource: KeySource | null; hybridValid: boolean | null; errorCode: string | null
}
const id = (value: unknown) => typeof value === 'string' && /^[0-9a-f]{32}$/.test(value)
const name = (value: unknown) => typeof value === 'string' && Array.from(value).length > 0 && Array.from(value).length <= 160 && !/[\x00-\x1f\x7f/\\]/.test(value)
function document(value: unknown): value is Document {
  return exact(value, ['documentId', 'displayName', 'sizeBytes']) && id(value.documentId) && name(value.displayName)
    && typeof value.sizeBytes === 'number' && Number.isSafeInteger(value.sizeBytes) && value.sizeBytes > 0 && value.sizeBytes <= 50 * 1024 * 1024 + 65536
}
function keys(value: unknown): value is KeySource {
  return exact(value, ['keySourceId', 'displayName', 'hybridKeyId', 'trust']) && id(value.keySourceId) && name(value.displayName)
    && typeof value.hybridKeyId === 'string' && /^hybrid-v1:[0-9a-f]{64}$/.test(value.hybridKeyId)
    && typeof value.trust === 'string' && ['vault-authenticated', 'unauthenticated-metadata'].includes(value.trust)
}
function job(value: unknown): value is Job {
  if (!exact(value, ['operationId', 'state', 'document', 'keySource', 'hybridValid', 'errorCode'])) return false
  if (value.state === 'idle') return value.operationId === null && value.document === null && value.keySource === null && value.hybridValid === null && value.errorCode === null
  if (!id(value.operationId) || !document(value.document) || !keys(value.keySource)) return false
  if (value.state === 'valid') return value.hybridValid === true && value.errorCode === null
  if (value.state === 'invalid') return value.hybridValid === false && value.errorCode === null
  if (value.state === 'failed') return value.hybridValid === null && typeof value.errorCode === 'string'
  return typeof value.state === 'string' && ['ready', 'queued', 'running'].includes(value.state) && value.hybridValid === null && value.errorCode === null
}
const active = (value: Job | null) => !!value && ['ready', 'queued', 'running'].includes(value.state)
const messages: Record<string, string> = {
  STALE_DOCUMENT: 'Choose the signed PDF again.', STALE_KEY_SOURCE: 'Choose the public-key source again.',
  DOCUMENT_CHANGED: 'The selected PDF changed. Choose it again.', 'vault.conflict': 'The public-key source changed. Select it again.',
  'vault.format': 'The encrypted vault header or public keys are invalid.', 'vault.profile': 'Unsupported encrypted vault profile.',
  STALE_SESSION: 'Select an encrypted vault, or authenticate a vault before using that source.',
  PDF_INVALID: 'Choose a supported PDF within the local size limit.', BUSY: 'Another native operation is in progress.',
  VERIFY_IO: 'The verification file could not be read safely. Check access and select it again.',
  VERIFY_FAILED: 'Verification could not complete. No mathematical result was established.',
}
class RequestError extends Error { constructor(message: string, readonly rejected = false) { super(message) } }
async function invoke(method: string, args: string[] = [], bounded = false): Promise<Record<string, unknown>> {
  let timer: number | undefined
  try {
    const host: unknown = (window as unknown as { pywebview?: unknown }).pywebview
    if (!record(host) || host.platform !== 'edgechromium' || !exact(host.api, verificationMethods) || typeof host.api[method] !== 'function') throw new Error()
    const call = (host.api[method] as (...args: string[]) => Promise<unknown>)(...args)
    const reply = bounded ? await Promise.race([call, new Promise((_, reject) => { timer = window.setTimeout(() => reject(new Error()), 2000) })]) : await call
    if (exact(reply, ['ok', 'protocolVersion', 'error']) && reply.ok === false && reply.protocolVersion === 1 && exact(reply.error, ['code', 'message'])) {
      throw new RequestError(typeof reply.error.code === 'string' ? messages[reply.error.code] ?? 'Native verification request rejected. Select the inputs again.' : 'Native request rejected.', reply.error.code !== 'VERIFY_UNCERTAIN')
    }
    const value = response(reply)
    if (!value) throw new Error()
    return value
  } catch (error) {
    if (error instanceof RequestError) throw error
    throw new RequestError('Native communication could not confirm a verification result. Reconcile this operation without submitting another job.')
  } finally { if (timer !== undefined) window.clearTimeout(timer) }
}
interface VerificationState {
  integrated: boolean; document: Document | null; keySource: KeySource | null; job: Job | null; busy: boolean
  uncertain: boolean; error: string | null; choosePdf: () => Promise<void>; chooseKeys: () => Promise<void>
  authenticated: (vaultId: string, sessionId: string) => Promise<void>; verify: () => Promise<void>; reconcile: () => Promise<void>
}
const Context = createContext<VerificationState | null>(null)
export function NativeVerificationProvider({ children }: PropsWithChildren) {
  const connection = useDesktopConnection(), integrated = connection.mode === 'desktop' && connection.capabilities.pdfVerification
  const [pdf, setPdf] = useState<Document | null>(null), [source, setSource] = useState<KeySource | null>(null), [current, setJob] = useState<Job | null>(null)
  const [pending, setPending] = useState(false), [submitting, setSubmitting] = useState(false), [uncertain, setUncertain] = useState(false), [error, setError] = useState<string | null>(null)
  const inflight = useRef(false), polling = useRef(false), operation = useRef<string | null>(null), generation = useRef(0), mounted = useRef(false)
  const read = async () => {
    if (!integrated || polling.current) return
    polling.current = true
    const epoch = generation.current, expected = operation.current
    try {
      const value = await invoke('get_verification_state', expected ? [expected] : [], true)
      if (!job(value) || expected !== null && value.operationId !== expected) throw new Error()
      if (mounted.current && generation.current === epoch) {
        setJob(value); setUncertain(false)
        if (value.document) setPdf(value.document)
        if (value.keySource) setSource(value.keySource)
        if (value.operationId) operation.current = value.operationId
        setError(value.state === 'failed' ? messages[value.errorCode ?? ''] ?? 'Verification could not complete. Select the inputs again.' : null)
      }
    } catch { if (mounted.current && generation.current === epoch && operation.current) setUncertain(true) }
    finally { polling.current = false }
  }
  useEffect(() => { mounted.current = true; if (integrated) void read(); return () => { mounted.current = false } }, [integrated])
  useEffect(() => {
    if (!integrated || !(submitting || active(current) || uncertain)) return
    const interval = window.setInterval(() => void read(), 200)
    return () => window.clearInterval(interval)
  }, [integrated, submitting, current?.state, uncertain])
  const busy = pending || active(current) || uncertain
  async function select(method: string, args: string[] = []) {
    if (!integrated || busy || inflight.current) return
    generation.current += 1; inflight.current = true; setPending(true); setError(null)
    // Starting a new selection invalidates the previous visible result even if
    // the dialog is cancelled. It can never imply verification of a new file.
    setJob(null); operation.current = null
    try {
      const value = await invoke(method, args), field = method === 'choose_verification_pdf' ? 'document' : 'keySource'
      if (!exact(value, [field, 'cancelled']) || typeof value.cancelled !== 'boolean') throw new Error()
      if (!value.cancelled) {
        if (field === 'document' && document(value.document)) setPdf(value.document)
        else if (field === 'keySource' && keys(value.keySource)) setSource(value.keySource)
        else throw new Error()
      }
    } catch (failure) {
      if (method === 'choose_verification_pdf') setPdf(null); else setSource(null)
      setError(failure instanceof RequestError ? failure.message : 'Native selection could not be validated.')
    } finally { inflight.current = false; setPending(false) }
  }
  async function verify() {
    if (!integrated || busy || inflight.current || !pdf || !source) return
    generation.current += 1; inflight.current = true; setPending(true); setSubmitting(true); setError(null); setJob(null)
    operation.current = crypto.randomUUID().replaceAll('-', '')
    try {
      const value = await invoke('verify_pdf', [pdf.documentId, source.keySourceId, operation.current])
      if (!job(value) || value.operationId !== operation.current) throw new Error()
      setJob(value); setUncertain(false)
    } catch (failure) {
      setError(failure instanceof RequestError ? failure.message : 'Verification outcome is not confirmed.')
      if (failure instanceof RequestError && failure.rejected) { operation.current = null; setUncertain(false) }
      else { setUncertain(true); await read() }
    } finally { inflight.current = false; setPending(false); setSubmitting(false) }
  }
  return <Context.Provider value={{ integrated, document: pdf, keySource: source, job: current, busy, uncertain, error,
    choosePdf: () => select('choose_verification_pdf'), chooseKeys: () => select('choose_verification_keys'),
    authenticated: (vaultId, sessionId) => id(vaultId) && id(sessionId) ? select('use_authenticated_vault_keys', [vaultId, sessionId]) : Promise.resolve(),
    verify, reconcile: read }}>{children}</Context.Provider>
}
export function useNativeVerification() {
  const value = useContext(Context)
  if (!value) throw new Error('Native verification provider missing')
  return value
}
