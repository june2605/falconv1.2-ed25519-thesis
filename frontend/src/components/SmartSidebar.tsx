import { useEffect, useId, useRef, useState, type FocusEvent, type PointerEvent as ReactPointerEvent } from 'react'
import { createPortal } from 'react-dom'
import { ArrowUpRight, CircleHelp, FilePenLine, LayoutDashboard, LockKeyhole, PanelLeftClose, PanelLeftOpen, Pin, PinOff, RotateCcw, Settings2, ShieldCheck } from 'lucide-react'
import type { PageId } from '../models'

export const navigation = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'sign', label: 'Sign Document', icon: FilePenLine },
  { id: 'verify', label: 'Verify Signature', icon: ShieldCheck },
  { id: 'vault', label: 'Key Vault', icon: LockKeyhole },
  { id: 'settings', label: 'Settings', icon: Settings2 },
] as const

type Mode = 'auto' | 'manual' | 'pinned'
const EXPAND_AT = 1340, COLLAPSE_AT = 1280, OPEN_DELAY = 140, CLOSE_DELAY = 220

export function SmartSidebar({ page, connected, status, detail, phase, onAbout }: {
  page: PageId; connected: boolean; status: string; detail: string; phase: string; onAbout: () => void
}) {
  const root = useRef<HTMLElement>(null), toggle = useRef<HTMLButtonElement>(null)
  const [mode, setMode] = useState<Mode>('auto')
  const [wide, setWide] = useState(() => window.innerWidth >= EXPAND_AT)
  const [open, setOpen] = useState(false)
  const [resizing, setResizing] = useState(false)
  const [tooltip, setTooltip] = useState<{ label: string; top: number; left: number } | null>(null)
  const timers = useRef<{ open?: number; close?: number; resize?: number }>({})
  const inside = useRef(false), blocked = useRef(false), fine = useRef(false), resizingNow = useRef(false)
  const autoEnabled = mode === 'auto', docked = wide && mode === 'pinned', expanded = docked || open
  const live = useRef({ mode, docked, expanded })
  live.current = { mode, docked, expanded }
  const navId = useId(), tooltipId = useId(), hintId = useId()

  function clear(kind: 'open' | 'close' | 'resize') {
    window.clearTimeout(timers.current[kind]); timers.current[kind] = undefined
  }
  function dismiss() {
    clear('open'); clear('close'); blocked.current = inside.current
    setOpen(false); setTooltip(null)
  }
  function restoreFocus() {
    const active = document.activeElement
    if (active instanceof HTMLElement && root.current?.contains(active) && active.closest('[data-expanded-only]')) toggle.current?.focus({ preventScroll: true })
  }
  function keyboardInside() {
    const active = document.activeElement
    return active instanceof HTMLElement && !!root.current?.contains(active) && active.matches(':focus-visible')
  }
  function closeLater() {
    clear('close')
    timers.current.close = window.setTimeout(() => {
      if (live.current.mode === 'auto' && !inside.current && !keyboardInside()) {
        restoreFocus(); setOpen(false); setTooltip(null)
      }
    }, CLOSE_DELAY)
  }
  useEffect(() => {
    const media = window.matchMedia('(hover: hover) and (pointer: fine)')
    const capability = () => { fine.current = media.matches }
    capability(); media.addEventListener('change', capability)
    const resize = () => {
      clear('open'); clear('close'); clear('resize')
      restoreFocus()
      resizingNow.current = true; setResizing(true); setTooltip(null)
      const width = root.current?.parentElement?.clientWidth ?? window.innerWidth
      setWide(current => current ? width > COLLAPSE_AT : width >= EXPAND_AT)
      timers.current.resize = window.setTimeout(() => {
        resizingNow.current = false; setResizing(false)
        if (live.current.mode === 'auto' && !inside.current && !keyboardInside()) closeLater()
      }, 180)
    }
    const outside = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) {
        if (live.current.mode === 'auto') closeLater()
        else if (!live.current.docked) dismiss()
      }
    }
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && live.current.expanded && !live.current.docked && !(event.target as HTMLElement)?.closest?.('[role="dialog"]')) {
        event.preventDefault(); restoreFocus(); dismiss()
      }
    }
    window.addEventListener('resize', resize)
    document.addEventListener('pointerdown', outside)
    document.addEventListener('keydown', escape)
    return () => {
      clear('open'); clear('close'); clear('resize')
      media.removeEventListener('change', capability)
      window.removeEventListener('resize', resize)
      document.removeEventListener('pointerdown', outside)
      document.removeEventListener('keydown', escape)
    }
  }, [])
  useEffect(() => { if (!expanded) restoreFocus() }, [expanded])

  function enter(event: ReactPointerEvent) {
    inside.current = true; clear('close')
    if (event.pointerType === 'touch' || !fine.current || live.current.mode !== 'auto' || blocked.current || resizingNow.current || live.current.expanded) return
    clear('open')
    timers.current.open = window.setTimeout(() => {
      if (live.current.mode === 'auto' && inside.current && !blocked.current && !resizingNow.current) { setOpen(true); setTooltip(null) }
    }, OPEN_DELAY)
  }
  function leave() {
    inside.current = false; blocked.current = false
    clear('open'); setTooltip(null); closeLater()
  }
  function focus(event: FocusEvent) {
    clear('close')
    const target = event.target as HTMLElement
    if (!live.current.expanded && target.closest('nav') && target.matches(':focus-visible')) {
      if (live.current.mode === 'auto') { setOpen(true); setTooltip(null) }
      else showTip(target, target.getAttribute('aria-label') ?? '')
    }
  }
  function showTip(target: HTMLElement, label: string) {
    if (live.current.expanded) return
    const rect = target.getBoundingClientRect()
    setTooltip({ label, top: Math.max(24, Math.min(window.innerHeight - 24, rect.top + rect.height / 2)), left: (root.current?.getBoundingClientRect().right ?? 72) + 8 })
  }
  function control() {
    clear('open'); clear('close'); setTooltip(null)
    if (expanded) {
      restoreFocus()
      if (mode === 'pinned') setMode('manual')
      dismiss()
    } else { blocked.current = true; setOpen(true) }
  }
  function enableAuto() {
    clear('open'); clear('close'); blocked.current = false; setTooltip(null)
    setMode('auto')
    if (inside.current || keyboardInside()) setOpen(true)
    else {
      setOpen(live.current.expanded)
      closeLater()
    }
  }
  function pin() {
    if (resizingNow.current) return
    if (mode === 'pinned') { enableAuto(); return }
    if (!wide) return
    clear('open'); clear('close'); setTooltip(null)
    setMode('pinned'); setOpen(false)
  }
  function automatic() {
    if (!autoEnabled) { enableAuto(); return }
    clear('open'); clear('close'); setTooltip(null); blocked.current = false
    setMode('manual'); setOpen(expanded)
  }
  const toggleName = expanded ? 'Collapse sidebar' : 'Expand sidebar'
  const toggleHint = `${toggleName} (Auto ${autoEnabled ? 'on' : 'off'})`
  return <>
    <aside ref={root} className="sidebar smart-sidebar" aria-label="Workspace sidebar" data-mode={mode}
      data-docked={docked} data-expanded={expanded} data-temporary={!docked && expanded} data-resizing={resizing} data-auto={autoEnabled}
      onPointerEnter={enter} onPointerLeave={leave} onFocusCapture={focus}
      onBlurCapture={event => { setTooltip(null); if (!event.currentTarget.contains(event.relatedTarget as Node)) closeLater() }}>
      <div className="sidebar-header"><a href="#/dashboard" className="brand" aria-label="HybridSign home">
        <img src="./mark.svg" width="36" height="36" alt="" /><span className="sidebar-brand-copy"><strong>HybridSign</strong><small>Hybrid Digital Signature</small></span>
      </a><div className="sidebar-controls">
        <button ref={toggle} className="icon-button sidebar-toggle" aria-label={toggleName} aria-expanded={expanded} aria-controls={navId} disabled={resizing} title={toggleHint}
          onClick={control} onPointerEnter={event => showTip(event.currentTarget, toggleHint)} onPointerLeave={() => setTooltip(null)}
          onFocus={event => showTip(event.currentTarget, toggleHint)} aria-describedby={tooltip?.label === toggleHint ? tooltipId : undefined}>
          {expanded ? <PanelLeftClose size={19} /> : <PanelLeftOpen size={19} />}
        </button>
        <button className="icon-button sidebar-pin" data-expanded-only aria-label={mode === 'pinned' ? 'Unpin sidebar' : 'Pin sidebar'} aria-pressed={mode === 'pinned'}
          disabled={(mode !== 'pinned' && !wide) || resizing} aria-describedby={!wide ? hintId : undefined} onClick={pin}>{mode === 'pinned' ? <PinOff size={18} /> : <Pin size={18} />}</button>
        <button className="text-button sidebar-auto" data-expanded-only aria-label="Automatic sidebar" aria-pressed={autoEnabled} disabled={resizing}
          title={autoEnabled ? 'Auto is on. The sidebar expands on hover and collapses when you move away.' : 'Auto is off. Select to expand on hover.'}
          onClick={automatic}><RotateCcw size={15} aria-hidden="true" />Auto {autoEnabled ? 'on' : 'off'}</button>
      </div></div>
      <div className="sidebar-scroll"><div className="sidebar-label" aria-hidden={!expanded}>WORKSPACE</div>
        <nav id={navId} aria-label="Main navigation">{navigation.map(({ id, label, icon: Icon }) => <a key={id} href={`#/${id}`}
          aria-label={label} aria-current={page === id ? 'page' : undefined} title={label} className={`nav-item ${page === id ? 'active' : ''}`}
          aria-describedby={tooltip?.label === label ? tooltipId : undefined}
          onPointerEnter={event => showTip(event.currentTarget, label)} onPointerLeave={() => setTooltip(null)}>
          <Icon size={19} strokeWidth={1.8} aria-hidden="true" /><span className="nav-label">{label}</span>{page === id && <span className="nav-dot" aria-hidden="true" />}
        </a>)}</nav>
      </div>
      <div className="sidebar-bottom">{!wide && <p id={hintId} className="sidebar-pin-hint" data-expanded-only>Pin on wider windows.</p>}<div className="sidebar-note" data-connected={connected} tabIndex={0} role="img" aria-label={detail}
        onPointerEnter={event => showTip(event.currentTarget, detail)} onPointerLeave={() => setTooltip(null)} onFocus={event => showTip(event.currentTarget, detail)}>
        <span className="status-dot" aria-hidden="true" /><span className="sidebar-status-copy" title={detail}>{status}</span><span className="badge sidebar-phase">{phase}</span>
      </div><button className="sidebar-about" aria-label="About this app" onClick={onAbout}
        onPointerEnter={event => showTip(event.currentTarget, 'About this app')} onPointerLeave={() => setTooltip(null)} onFocus={event => showTip(event.currentTarget, 'About this app')}>
        <CircleHelp size={18} aria-hidden="true" /><span>About this app</span><ArrowUpRight size={14} aria-hidden="true" />
      </button></div>
    </aside>
    {tooltip && !expanded && createPortal(<span id={tooltipId} className="sidebar-tooltip" role="tooltip" style={{ left: tooltip.left, top: tooltip.top }}>{tooltip.label}</span>, document.body)}
  </>
}
