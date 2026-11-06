import { useEffect, useId, useRef, useState } from 'react'
import { Check, ChevronDown, Copy } from 'lucide-react'
import { Button } from './ui'

const confirmation = 'Full ID copied.'
const copyError = 'Clipboard unavailable. Select the full ID to copy manually.'

/** Presentation only. Always copy the original public identifier unchanged. */
export function HybridKeyId({ value }: { value: string }) {
  const [expanded, setExpanded] = useState(false)
  const [feedback, setFeedback] = useState<{ kind: 'copied' | 'error'; request: number } | null>(null)
  const timer = useRef<number | undefined>(undefined)
  const request = useRef(0)
  const regionId = useId()
  useEffect(() => {
    request.current += 1
    setExpanded(false); setFeedback(null)
    return () => {
      request.current += 1 // Ignore clipboard completions from an old value/unmounted view.
      window.clearTimeout(timer.current)
      timer.current = undefined
    }
  }, [value])
  async function copy() {
    const current = ++request.current
    window.clearTimeout(timer.current)
    timer.current = undefined
    setFeedback(null)
    try {
      await navigator.clipboard.writeText(value)
      if (current !== request.current) return
      setFeedback({ kind: 'copied', request: current })
      timer.current = window.setTimeout(() => {
        timer.current = undefined
        if (current === request.current) setFeedback(null)
      }, 2000)
    } catch {
      if (current !== request.current) return
      setExpanded(true); setFeedback({ kind: 'error', request: current })
    }
  }
  const copied = feedback?.kind === 'copied'
  const message = copied ? confirmation : feedback?.kind === 'error' ? copyError : ''
  const compact = value.length > 34 ? `${value.slice(0, 18)}…${value.slice(-8)}` : value
  return <div className="hybrid-key-id" role="group" aria-label="Hybrid key ID">
    <div className="key-id-line"><code className="key-id-compact" aria-label="Abbreviated public-key pair identifier">{compact}</code>
      <div className="key-id-controls"><Button variant="ghost" className="key-id-copy" aria-label="Copy full ID" onClick={() => void copy()}>
        {copied ? <Check size={15} aria-hidden="true" /> : <Copy size={15} aria-hidden="true" />}
        <span className="key-id-copy-label" aria-hidden="true" data-confirmation={confirmation}><span>{copied ? confirmation : 'Copy full ID'}</span></span>
      </Button>
      <Button variant="ghost" className="key-id-toggle" aria-expanded={expanded} aria-controls={regionId} onClick={() => setExpanded(current => !current)}>
        View full ID<ChevronDown size={15} aria-hidden="true" />
      </Button></div>
    </div>
    <div id={regionId} hidden={!expanded} className="key-id-disclosure">
      <code className="key-id-full" tabIndex={0} aria-label="Full hybrid key ID">{value}</code>
      {feedback?.kind === 'error' && <p className="key-id-error">{copyError}</p>}
    </div>
    <span role="status" aria-live="polite" aria-atomic="true" className="sr-only"><span key={feedback?.request ?? 'idle'}>{message}</span></span>
  </div>
}
