import { useEffect, useRef, useState } from 'react'
import { ArrowUpRight, ChevronRight, CircleHelp, FilePenLine, Layers2, LayoutDashboard, LockKeyhole, Settings2, ShieldCheck } from 'lucide-react'
import { usePage } from './hooks'
import type { PageId } from './models'
import { Dashboard } from './pages/Dashboard'
import { SignDocument } from './pages/SignDocument'
import { VerifySignature } from './pages/VerifySignature'
import { KeyVault } from './pages/KeyVault'
import { Settings } from './pages/Settings'
import { VaultDialogs } from './components/VaultDialogs'
import { TaskFooterHost } from './components/TaskFooter'
import { Badge, Toasts } from './components/ui'
import { useWorkspace } from './state/workspace'
import { useDesktopConnection } from './native/status'
import { useNativeVault } from './native/vault'

const navigation = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'sign', label: 'Sign Document', icon: FilePenLine },
  { id: 'verify', label: 'Verify Signature', icon: ShieldCheck },
  { id: 'vault', label: 'Key Vault', icon: LockKeyhole },
  { id: 'settings', label: 'Settings', icon: Settings2 },
] as const

const screens: Record<PageId, React.ComponentType> = { dashboard: Dashboard, sign: SignDocument, verify: VerifySignature, vault: KeyVault, settings: Settings }

export default function App() {
  const page = usePage()
  const { setDialog } = useWorkspace()
  const desktop = useDesktopConnection().mode === 'desktop'
  const { integrated } = useNativeVault()
  const main = useRef<HTMLElement>(null)
  const [footerHost, setFooterHost] = useState<HTMLDivElement | null>(null)
  const firstRender = useRef(true)
  const Screen = screens[page]
  useEffect(() => {
    if (firstRender.current) { firstRender.current = false; return }
    main.current?.querySelector('h1')?.focus({ preventScroll: true })
    main.current?.scrollTo({ top: 0 })
  }, [page])

  return <TaskFooterHost.Provider value={footerHost}><div className="app-shell">
    <a className="skip-link" href="#main-content" onClick={event => { event.preventDefault(); main.current?.focus() }}>Skip to content</a>
    <aside className="sidebar">
      <a href="#/dashboard" className="brand" aria-label="HybridSign home"><img src="./mark.svg" width="36" height="36" alt="" /><span><strong>HybridSign</strong><small>Hybrid Digital Signature</small></span></a>
      <div className="sidebar-label">WORKSPACE</div>
      <nav aria-label="Main navigation">{navigation.map(({ id, label, icon: Icon }) => <a key={id} href={`#/${id}`} aria-current={page === id ? 'page' : undefined} title={label} className={`nav-item ${page === id ? 'active' : ''}`}><Icon size={19} strokeWidth={1.8} aria-hidden="true" /><span>{label}</span>{page === id && <span className="nav-dot" />}</a>)}</nav>
      <div className="sidebar-bottom"><div className="sidebar-note"><span className="status-dot" /><span title={integrated ? 'Local vault operations connected. PDF signing and verification remain unavailable.' : desktop ? 'Vault, signing and verification integration is not ready.' : undefined}>{integrated ? 'Vault connected · PDF unavailable' : desktop ? 'Vault / PDF not integrated' : 'Native bridge unavailable'}</span><Badge>{integrated ? '4B.2A' : '4B.1'}</Badge></div><button className="sidebar-about" onClick={() => setDialog('about')}><CircleHelp size={16} aria-hidden="true" /><span>About this prototype</span><ArrowUpRight size={14} aria-hidden="true" /></button></div>
    </aside>
    <div className="workspace"><header className="topbar"><div className="breadcrumb"><Layers2 size={18} aria-hidden="true" /><span>Workspace</span><ChevronRight size={13} aria-hidden="true" /><strong>{navigation.find(item => item.id === page)?.label}</strong></div><div className="topbar-actions"><span className="preview-indicator" aria-live="polite" title={integrated ? 'Local encrypted vault operations are connected. PDF signing and verification are not integrated.' : desktop ? 'Desktop shell connected. Vault, signing and verification are not integrated.' : 'Browser UI preview; native connection unavailable.'}><span className="status-dot" />{desktop ? 'Desktop Connected' : 'UI PREVIEW'}</span><span className="topbar-divider" /><button className="icon-button" aria-label="About HybridSign" onClick={() => setDialog('about')}><CircleHelp size={20} strokeWidth={1.7} /></button></div></header>
      <main ref={main} tabIndex={-1} id="main-content"><div className="page-container"><Screen key={page} /></div></main>
      <div className="task-actions-host" ref={setFooterHost} />
    </div><VaultDialogs /><Toasts />
  </div></TaskFooterHost.Provider>
}
