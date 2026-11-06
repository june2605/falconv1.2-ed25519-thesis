import { createContext, useContext, useEffect, useRef, useState, type PropsWithChildren } from 'react'
import { exact, record, response, signingApi } from './desktop'
import { useNativeVerification } from './verification'
import { useDesktopConnection } from './status'

export interface NativePdf { documentId: string; displayName: string; sizeBytes: number }
interface SigningJob {
  operationId: string | null
  state: 'idle' | 'ready' | 'queued' | 'running' | 'completed' | 'failed' | 'outcome-uncertain' | 'cancelled'
  document: NativePdf | null
  outputName: string | null
  hybridKeyId: string | null
  selfVerified: boolean
  errorCode: string | null
}
const active = (job: SigningJob | null) => !!job && ['ready', 'queued', 'running'].includes(job.state)
const identifier = (value: unknown) => typeof value === 'string' && /^[0-9a-f]{32}$/.test(value)
const name = (value: unknown) => typeof value === 'string' && Array.from(value).length > 0 && Array.from(value).length <= 160 && !/[\x00-\x1f\x7f/\\]/.test(value)
function pdf(value: unknown): value is NativePdf {
  return exact(value, ['documentId', 'displayName', 'sizeBytes']) && identifier(value.documentId) && name(value.displayName)
    && typeof value.sizeBytes === 'number' && Number.isSafeInteger(value.sizeBytes) && value.sizeBytes > 0 && value.sizeBytes <= 50 * 1024 * 1024
}
function job(value: unknown): value is SigningJob {
  if (!exact(value, ['operationId', 'state', 'document', 'outputName', 'hybridKeyId', 'selfVerified', 'errorCode'])) return false
  if (typeof value.state !== 'string' || !['idle', 'ready', 'queued', 'running', 'completed', 'failed', 'outcome-uncertain', 'cancelled'].includes(value.state)
    || !(value.operationId === null || identifier(value.operationId)) || !(value.document === null || pdf(value.document))
    || !(value.outputName === null || name(value.outputName)) || typeof value.selfVerified !== 'boolean'
    || !(value.hybridKeyId === null || typeof value.hybridKeyId === 'string' && /^hybrid-v1:[0-9a-f]{64}$/.test(value.hybridKeyId))
    || !(value.errorCode === null || typeof value.errorCode === 'string')) return false
  return value.state === 'idle' ? value.operationId === null && !value.selfVerified : identifier(value.operationId) && !!value.document && !!value.hybridKeyId
    && (value.state === 'completed' ? value.selfVerified === true && !!value.outputName && value.errorCode === null : value.selfVerified === false)
}
class NativeSigningError extends Error {
  constructor(message: string, readonly rejected = false) { super(message) }
}
const errors: Record<string, string> = {
  PDF_INVALID: 'Choose a supported unsigned PDF up to 50 MiB. Already-signed or reserved-marker files are rejected.',
  STALE_SESSION: 'Unlock the native vault again before signing.', STALE_DOCUMENT: 'Choose the PDF again.',
  DOCUMENT_CHANGED: 'The selected PDF changed. Choose it again.', BUSY: 'A native operation is already in progress.',
}
async function invoke(method: string, args: string[] = [], bounded = false): Promise<unknown> {
  let timer: number | undefined
  try {
    const host: unknown = (window as unknown as { pywebview?: unknown }).pywebview
    if (!record(host) || host.platform !== 'edgechromium' || !signingApi(host.api) || typeof host.api[method] !== 'function') throw new Error()
    const call = (host.api[method] as (...args: string[]) => Promise<unknown>)(...args)
    const reply = bounded ? await Promise.race([call, new Promise((_, reject) => { timer = window.setTimeout(() => reject(new Error()), 2000) })]) : await call
    if (exact(reply, ['ok', 'protocolVersion', 'error']) && reply.ok === false && reply.protocolVersion === 1 && exact(reply.error, ['code', 'message'])) {
      throw new NativeSigningError(typeof reply.error.code === 'string' ? errors[reply.error.code] ?? 'Native request rejected. Inspect the selected output location before retrying.' : 'Native request rejected.', reply.error.code !== 'SIGN_UNCERTAIN')
    }
    const value = response(reply)
    if (!value) throw new Error()
    return value
  } catch (error) {
    if (error instanceof NativeSigningError) throw error
    throw new NativeSigningError('Native communication could not confirm the outcome. Reconcile status and inspect the output location before starting another job.')
  } finally { if (timer !== undefined) window.clearTimeout(timer) }
}
interface SigningState {
  integrated: boolean; document: NativePdf | null; job: SigningJob | null; busy: boolean
  uncertain: boolean; error: string | null; choose: () => Promise<void>; reconcile: () => Promise<void>; reset: () => void
  sign: (vaultId: string, sessionId: string) => Promise<void>
}
const Context = createContext<SigningState | null>(null)

export function NativeSigningProvider({ children }: PropsWithChildren) {
  const verificationBusy = useNativeVerification().busy
  const connection = useDesktopConnection()
  const integrated = connection.mode === 'desktop' && connection.capabilities.pdfSigning
  const [document, setDocument] = useState<NativePdf | null>(null), [current, setJob] = useState<SigningJob | null>(null)
  const [pending, setPending] = useState(false), [submitting, setSubmitting] = useState(false), [uncertain, setUncertain] = useState(false), [error, setError] = useState<string | null>(null)
  const inflight = useRef(false), polling = useRef(false), mounted = useRef(false), operation = useRef<string | null>(null)
  const generation = useRef(0)
  const read = async () => {
    if (!integrated || polling.current) return
    polling.current = true
    const epoch = generation.current, expected = operation.current
    try {
      const value = await invoke('get_signing_state', operation.current ? [operation.current] : [], true)
      if (!job(value) || expected !== null && value.operationId !== expected) throw new Error()
      if (mounted.current && epoch === generation.current) {
        setJob(value); setUncertain(false)
        if (value.document) setDocument(value.document)
        if (value.operationId) operation.current = value.operationId
        if (['completed', 'cancelled'].includes(value.state)) setError(null)
      }
    } catch {
      if (mounted.current && epoch === generation.current && operation.current) { setUncertain(true); setError('Signing outcome not confirmed. Reconcile native status; a PDF may already exist.') }
    } finally { polling.current = false }
  }
  useEffect(() => {
    mounted.current = true
    if (integrated) void read()
    return () => { mounted.current = false }
    // The connection gates startup; changing public job state must not restart initialization.
  }, [integrated])
  useEffect(() => {
    if (!integrated || !(submitting || active(current) || uncertain)) return
    const interval = window.setInterval(() => void read(), 200)
    return () => window.clearInterval(interval)
  }, [integrated, submitting, current?.state, uncertain])
  const busy = pending || active(current) || uncertain || verificationBusy
  async function choose() {
    if (!integrated || inflight.current || busy) return
    generation.current += 1
    inflight.current = true; setPending(true); setError(null)
    try {
      const value = await invoke('choose_pdf')
      if (!exact(value, ['document', 'cancelled']) || typeof value.cancelled !== 'boolean' || !(value.document === null || pdf(value.document))) throw new Error()
      if (!value.cancelled && value.document) { setDocument(value.document as unknown as NativePdf); setJob(null); operation.current = null }
    } catch (failure) { setError(failure instanceof NativeSigningError ? failure.message : 'Native PDF selection could not be validated.'); setDocument(null) }
    finally { inflight.current = false; setPending(false) }
  }
  async function sign(vaultId: string, sessionId: string) {
    if (!integrated || !document || inflight.current || busy || !identifier(vaultId) || !identifier(sessionId)) return
    generation.current += 1
    inflight.current = true; setPending(true); setSubmitting(true); setError(null)
    operation.current = crypto.randomUUID().replaceAll('-', '')
    try {
      const value = await invoke('sign_pdf', [document.documentId, vaultId, sessionId, operation.current])
      if (!job(value) || value.operationId !== operation.current) throw new Error()
      setJob(value); setUncertain(false)
    } catch (failure) {
      setError(failure instanceof NativeSigningError ? failure.message : 'Native signing outcome is not confirmed.')
      if (failure instanceof NativeSigningError && failure.rejected) {
        setUncertain(false); setJob(null); operation.current = null
      } else {
        setUncertain(true)
        await read()  // Reconcile this same ID, never resubmit automatically.
      }
    } finally { inflight.current = false; setPending(false); setSubmitting(false) }
  }
  return <Context.Provider value={{ integrated, document, job: current, busy, uncertain, error, choose, sign, reconcile: read,
    reset: () => { if (!busy) { generation.current += 1; setJob(null); setError(null); operation.current = null } } }}>{children}</Context.Provider>
}

export function useNativeSigning() {
  const value = useContext(Context)
  if (!value) throw new Error('Native signing provider missing')
  return value
}
