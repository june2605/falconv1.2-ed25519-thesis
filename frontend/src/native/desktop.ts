/** Phase 4B.1 metadata only. This does not implement NativeBridgeV1 operations. */
export interface DesktopInfo {
  applicationName: 'HybridSign'
  applicationVersion: '0.1.0'
  runtime: 'pywebview-edgechromium'
  desktopStatus: 'connected'
}

export interface DesktopCapabilities {
  nativeShell: true
  vaultOperations: false
  pdfSigning: false
  pdfVerification: false
  accountRegistry: false
}

export type DesktopConnection = { mode: 'preview'; reason: 'unavailable' | 'timeout' | 'invalid-response' }
  | { mode: 'desktop'; info: DesktopInfo; capabilities: DesktopCapabilities }

interface MetadataApi {
  get_app_info: () => Promise<unknown>
  get_capabilities: () => Promise<unknown>
}

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function exact(value: unknown, keys: string[]): value is Record<string, unknown> {
  return record(value) && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key))
}

function response(value: unknown): Record<string, unknown> | null {
  return exact(value, ['ok', 'protocolVersion', 'data']) && value.ok === true && value.protocolVersion === 1 && record(value.data) ? value.data : null
}

function metadataApi(): MetadataApi | null {
  const host: unknown = (window as unknown as { pywebview?: unknown }).pywebview
  if (!record(host) || host.platform !== 'edgechromium' || !exact(host.api, ['get_app_info', 'get_capabilities'])) return null
  return typeof host.api.get_app_info === 'function' && typeof host.api.get_capabilities === 'function' ? host.api as unknown as MetadataApi : null
}

export function connectDesktop(signal: AbortSignal, timeoutMs = 3000): Promise<DesktopConnection> {
  return new Promise(resolve => {
    let settled = false, started = false
    const finish = (value: DesktopConnection) => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      window.removeEventListener('pywebviewready', attempt)
      signal.removeEventListener('abort', aborted)
      resolve(value)
    }
    const aborted = () => finish({ mode: 'preview', reason: 'unavailable' })
    const attempt = () => {
      if (settled || started) return
      let api: MetadataApi | null
      try { api = metadataApi() }
      catch { finish({ mode: 'preview', reason: 'invalid-response' }); return }
      if (!api) return  // A pywebview object alone is not readiness/capability proof.
      started = true
      Promise.all([Promise.resolve().then(() => api.get_app_info()), Promise.resolve().then(() => api.get_capabilities())]).then(([infoReply, capsReply]) => {
        const info = response(infoReply), caps = response(capsReply)
        if (!exact(info, ['applicationName', 'applicationVersion', 'runtime', 'desktopStatus']) || info.applicationName !== 'HybridSign' || info.applicationVersion !== '0.1.0' || info.runtime !== 'pywebview-edgechromium' || info.desktopStatus !== 'connected'
          || !exact(caps, ['nativeShell', 'vaultOperations', 'pdfSigning', 'pdfVerification', 'accountRegistry']) || caps.nativeShell !== true || caps.vaultOperations !== false || caps.pdfSigning !== false || caps.pdfVerification !== false || caps.accountRegistry !== false) {
          finish({ mode: 'preview', reason: 'invalid-response' }); return
        }
        finish({ mode: 'desktop', info: info as unknown as DesktopInfo, capabilities: caps as unknown as DesktopCapabilities })
      }).catch(() => finish({ mode: 'preview', reason: 'invalid-response' }))
    }
    const delay = Number.isFinite(timeoutMs) && timeoutMs > 0 ? Math.min(timeoutMs, 3000) : 3000
    const timer = window.setTimeout(() => finish({ mode: 'preview', reason: 'timeout' }), delay)
    window.addEventListener('pywebviewready', attempt)
    signal.addEventListener('abort', aborted, { once: true })
    if (signal.aborted) aborted()
    else attempt()
  })
}
