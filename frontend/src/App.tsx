import { useEffect, useRef, useState } from 'react'
import { ChevronRight, CircleHelp, Layers2 } from 'lucide-react'
import { usePage } from './hooks'
import type { PageId } from './models'
import { Dashboard } from './pages/Dashboard'
import { SignDocument } from './pages/SignDocument'
import { VerifySignature } from './pages/VerifySignature'
import { KeyVault } from './pages/KeyVault'
import { Settings } from './pages/Settings'
import { VaultDialogs } from './components/VaultDialogs'
import { TaskFooterHost } from './components/TaskFooter'
import { Toasts } from './components/ui'
import { SmartSidebar, navigation } from './components/SmartSidebar'
import { useWorkspace } from './state/workspace'
import { useDesktopConnection } from './native/status'
import { useNativeVault } from './native/vault'
import { useNativeSigning } from './native/signing'
import { useNativeVerification } from './native/verification'

const screens: Record<PageId, React.ComponentType> = { dashboard: Dashboard, sign: SignDocument, verify: VerifySignature, vault: KeyVault, settings: Settings }

export default function App() {
  const page = usePage()
  const { setDialog } = useWorkspace()
  const desktop = useDesktopConnection().mode === 'desktop'
  const { integrated } = useNativeVault()
  const signing = useNativeSigning().integrated
  const verifying = useNativeVerification().integrated
  const main = useRef<HTMLElement>(null)
  const [footerHost, setFooterHost] = useState<HTMLDivElement | null>(null)
  const firstRender = useRef(true)
  const Screen = screens[page]
  useEffect(() => {
    if (firstRender.current) { firstRender.current = false; return }
    main.current?.querySelector('h1')?.focus({ preventScroll: true })
    main.current?.scrollTo({ top: 0 })
  }, [page])
  useEffect(() => {
    let frame = 0
    const resize = () => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => {
        const active = document.activeElement
        if (active instanceof HTMLElement && active !== main.current && active.matches('button,input,select,summary,[tabindex]') && main.current?.contains(active)) {
          active.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'instant' })
        }
      })
    }
    window.addEventListener('resize', resize)
    return () => { cancelAnimationFrame(frame); window.removeEventListener('resize', resize) }
  }, [])

  return <TaskFooterHost.Provider value={footerHost}><div className="app-shell">
    <a className="skip-link" href="#main-content" onClick={event => { event.preventDefault(); main.current?.focus() }}>Skip to content</a>
    <SmartSidebar page={page} connected={desktop} onAbout={() => setDialog('about')}
      status={verifying ? 'PDF tools available' : signing ? 'PDF signing available' : integrated ? 'Key vault available' : desktop ? 'PDF tools unavailable' : 'Browser preview'}
      detail={verifying ? 'Sign and verify PDFs on this device.' : signing ? 'Signing is available. Standalone verification is unavailable in this version.' : integrated ? 'You can manage a local vault. PDF tools are unavailable in this version.' : desktop ? 'Vault and PDF tools are unavailable in this version.' : 'Browser preview with example results.'}
      phase={desktop ? '0.1.0' : 'UI PREVIEW'} />
    <div className="workspace"><header className="topbar"><div className="breadcrumb"><Layers2 size={18} aria-hidden="true" /><span>Workspace</span><ChevronRight size={13} aria-hidden="true" /><strong>{navigation.find(item => item.id === page)?.label}</strong></div><div className="topbar-actions"><span className="preview-indicator" aria-live="polite" title={verifying ? 'Sign and verify PDFs on this device.' : signing ? 'Signing is available. Standalone verification is unavailable in this version.' : integrated ? 'You can manage a local vault. PDF tools are unavailable in this version.' : desktop ? 'Vault and PDF tools are unavailable in this version.' : 'Browser preview with example results.'}><span className="status-dot" />{desktop ? 'Desktop' : 'UI PREVIEW'}</span><span className="topbar-divider" /><button className="icon-button" aria-label="About HybridSign" onClick={() => setDialog('about')}><CircleHelp size={20} strokeWidth={1.7} /></button></div></header>
      <main ref={main} tabIndex={-1} id="main-content"><div className="page-container"><Screen key={page} /></div></main>
      <div className="task-actions-host" ref={setFooterHost} />
    </div><VaultDialogs /><Toasts />
  </div></TaskFooterHost.Provider>
}
