import * as Dialog from '@radix-ui/react-dialog'
import { Check, CheckCircle2, Info, LoaderCircle, TriangleAlert, X, type LucideIcon } from 'lucide-react'
import { useEffect, useRef, type ButtonHTMLAttributes, type PropsWithChildren, type ReactNode } from 'react'
import { useWorkspace } from '../state/workspace'

export function Button({ variant = 'primary', busy, className = '', children, ...props }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost' | 'danger'; busy?: boolean }) {
  return <button type="button" className={`button button-${variant} ${className}`} aria-busy={busy || undefined} {...props} disabled={props.disabled || busy}>
    {busy && <LoaderCircle size={16} className="spin" aria-hidden="true" />}{children}
  </button>
}

export function Badge({ tone = 'neutral', children }: PropsWithChildren<{ tone?: 'neutral' | 'indigo' | 'success' | 'warning' | 'error' }>) {
  return <span className={`badge badge-${tone}`}>{children}</span>
}

export function IconTile({ icon: Icon, tone = 'neutral', small = false }: { icon: LucideIcon; tone?: 'neutral' | 'indigo' | 'success'; small?: boolean }) {
  return <span className={`icon-tile icon-tile-${tone} ${small ? 'icon-tile-small' : ''}`}><Icon size={small ? 18 : 22} strokeWidth={1.7} aria-hidden="true" /></span>
}

export function PageHeader({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description: string; action?: ReactNode }) {
  return <div className="page-heading"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h1 tabIndex={-1}>{title}</h1><p>{description}</p></div>{action && <div className="page-actions">{action}</div>}</div>
}

export function PreviewNote({ children = 'UI preview only. No cryptographic operations run in this prototype.' }: PropsWithChildren) {
  return <div className="preview-note"><Info size={15} aria-hidden="true" /><span>{children}</span></div>
}

export function Notice({ tone = 'info', title, children }: PropsWithChildren<{ tone?: 'info' | 'warning' | 'error' | 'success'; title?: string }>) {
  const Icon = tone === 'error' || tone === 'warning' ? TriangleAlert : tone === 'success' ? CheckCircle2 : Info
  return <div className={`notice notice-${tone}`} role={tone === 'error' ? 'alert' : undefined}><Icon size={18} aria-hidden="true" /><div>{title && <strong>{title}</strong>}<div>{children}</div></div></div>
}

export function Modal({ open, onOpenChange, title, description, children, footer, icon: Icon = Info }: PropsWithChildren<{
  open: boolean; onOpenChange: (open: boolean) => void; title: string; description: string; footer?: ReactNode; icon?: LucideIcon;
}>) {
  const returnFocus = useRef<HTMLElement | null>(null)
  return <Dialog.Root open={open} onOpenChange={onOpenChange}><Dialog.Portal><Dialog.Overlay className="dialog-overlay" />
    <Dialog.Content className="dialog-content" onOpenAutoFocus={() => { returnFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null }} onCloseAutoFocus={event => {
      event.preventDefault()
      // A successful demo unlock replaces its opener with the next-step action.
      const target = returnFocus.current?.isConnected ? returnFocus.current : document.querySelector<HTMLElement>('.task-action-buttons .button-primary:not(:disabled)')
      target?.focus({ preventScroll: true })
    }}><div className="dialog-top"><IconTile icon={Icon} tone="indigo" /><Badge tone="indigo">UI PREVIEW</Badge></div>
      <Dialog.Title className="dialog-title">{title}</Dialog.Title><Dialog.Description className="dialog-description">{description}</Dialog.Description>
      <div className="dialog-body">{children}</div>{footer && <div className="dialog-footer">{footer}</div>}
      <Dialog.Close className="icon-button dialog-close" aria-label="Close dialog"><X size={18} /></Dialog.Close>
    </Dialog.Content>
  </Dialog.Portal></Dialog.Root>
}

function Toast({ id, title, detail, tone }: { id: number; title: string; detail?: string; tone: 'info' | 'success' | 'error' }) {
  const { dismissToast } = useWorkspace()
  useEffect(() => {
    const timeout = window.setTimeout(() => dismissToast(id), 6500)
    return () => window.clearTimeout(timeout)
  }, [id, dismissToast])
  const Icon = tone === 'success' ? CheckCircle2 : tone === 'error' ? TriangleAlert : Info
  return <div className={`toast toast-${tone}`}><Icon size={19} aria-hidden="true" /><div><strong>{title}</strong>{detail && <p>{detail}</p>}</div>
    <button className="icon-button" aria-label={`Dismiss ${title}`} onClick={() => dismissToast(id)}><X size={16} /></button></div>
}

export function Toasts() {
  const { toasts } = useWorkspace()
  return <div className="toast-region" role="status" aria-live="polite" aria-atomic="false">{toasts.map(toast => <Toast key={toast.id} {...toast} />)}</div>
}

export function StepHeading({ number, title, complete }: { number: number; title: string; complete?: boolean }) {
  return <h2 className="step-heading"><span className={complete ? 'step-number complete' : 'step-number'}>{complete ? <Check size={13} aria-hidden="true" /> : number}</span>{title}</h2>
}

export function DetailsRow({ label, children }: PropsWithChildren<{ label: string }>) {
  return <div className="details-row"><dt>{label}</dt><dd>{children}</dd></div>
}
