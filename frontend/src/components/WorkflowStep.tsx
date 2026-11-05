import { Check, ChevronDown, type LucideIcon } from 'lucide-react'
import type { PropsWithChildren } from 'react'

export function WorkflowStep({ number, title, active, complete, disabled, summary, onSelect, children }: PropsWithChildren<{
  number: number; title: string; active: boolean; complete?: boolean; disabled?: boolean; summary?: string; onSelect: () => void;
}>) {
  const Icon: LucideIcon = complete ? Check : ChevronDown
  return <section className={`progressive-step ${active ? 'is-active' : ''}`}>
    <h2><button id={`sign-step-${number}`} type="button" className="step-toggle" aria-label={`${title} step`} aria-expanded={active} aria-controls={`sign-panel-${number}`} disabled={disabled} onClick={onSelect}>
      <span className={`step-number ${complete ? 'complete' : ''}`}>{complete ? <Check size={14} aria-hidden="true" /> : number}</span>
      <span className="step-heading-copy"><strong>{title}</strong>{!active && summary && <small>{summary}</small>}</span>
      <Icon size={16} className="step-toggle-icon" aria-hidden="true" />
    </button></h2>
    <div id={`sign-panel-${number}`} className="step-body" hidden={!active}>{children}</div>
  </section>
}
