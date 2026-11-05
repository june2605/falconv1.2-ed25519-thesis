import { useEffect, useRef, useState } from 'react'
import type { PageId } from './models'

export const pages: PageId[] = ['dashboard', 'sign', 'verify', 'vault', 'settings']
export function navigate(page: PageId): void { window.location.hash = `/${page}` }

function currentPage(): PageId {
  const value = window.location.hash.replace(/^#\/?/, '')
  return pages.includes(value as PageId) ? value as PageId : 'dashboard'
}

export function usePage(): PageId {
  const [page, setPage] = useState(currentPage)
  useEffect(() => {
    const update = () => setPage(currentPage())
    window.addEventListener('hashchange', update)
    return () => window.removeEventListener('hashchange', update)
  }, [])
  return page
}

export function usePreviewTask<T>() {
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<T | null>(null)
  const [error, setError] = useState('')
  const controller = useRef<AbortController | null>(null)
  useEffect(() => () => controller.current?.abort(), [])

  async function run(task: (signal: AbortSignal) => Promise<T>, onDone?: (result: T) => void) {
    controller.current?.abort()
    const active = new AbortController()
    controller.current = active
    setBusy(true); setResult(null); setError('')
    try {
      const value = await task(active.signal)
      if (!active.signal.aborted) { setResult(value); onDone?.(value) }
    } catch (cause) {
      if (!active.signal.aborted) setError(cause instanceof Error ? cause.message : 'The UI preview could not complete.')
    } finally {
      if (!active.signal.aborted) setBusy(false)
    }
  }

  function reset() { controller.current?.abort(); setBusy(false); setResult(null); setError('') }
  return { busy, result, error, run, reset }
}
