import { ArrowDown, ArrowRight, ArrowUpRight, Check, Clock3, FilePenLine, Files, Fingerprint, LockKeyhole, ShieldCheck } from 'lucide-react'
import { navigate } from '../hooks'
import { useWorkspace } from '../state/workspace'
import { Badge, IconTile, PageHeader } from '../components/ui'
import { PaperPreview } from '../components/DocumentPreview'
import { NativeVaultSummary } from '../components/NativeVault'
import { useNativeVault } from '../native/vault'

export function Dashboard() {
  const { vault, activities, clearActivity, setDialog } = useWorkspace()
  const { integrated } = useNativeVault()
  return <div className="dashboard">
    <PageHeader title="Your digital signing workspace" description="Prepare documents and explore the hybrid signing workflow." />
    <div className="dashboard-actions">
      <a href="#/sign" className="action-card action-sign"><div className="action-card-copy"><IconTile icon={FilePenLine} tone="indigo" /><h2>Sign a document</h2><p>Choose a PDF and explore the<br className="wide-break" /> demo signing workflow.</p><span className="button button-primary">Sign Document <ArrowRight size={16} aria-hidden="true" /></span></div><div className="hero-document" aria-hidden="true"><PaperPreview /><span className="document-seal"><Check size={17} /></span></div></a>
      <a href="#/verify" className="action-card action-verify"><IconTile icon={ShieldCheck} /><div><h2>Verify a signature</h2><p>Explore separate results for both<br className="wide-break" /> signature layers.</p></div><span className="action-link">Verify Signature <ArrowUpRight size={17} aria-hidden="true" /></span><div className="verify-decoration" aria-hidden="true"><ShieldCheck size={112} strokeWidth={.65} /></div></a>
    </div>
    <div className="dashboard-info">
      {integrated ? <NativeVaultSummary /> : <section className="card vault-summary"><div className="section-heading"><h2>Your key vault</h2><Badge tone="indigo">DEMO</Badge></div><div className="vault-summary-content"><IconTile icon={LockKeyhole} /><div><h3>{vault?.name ?? 'No demo vault selected'}</h3><p>{vault ? 'Ed25519 + Falcon-512' : 'Create a demo vault to explore the workflow.'}</p></div><Badge tone={vault?.state === 'unlocked' ? 'success' : 'neutral'}>{vault ? vault.state === 'locked' ? 'Locked' : 'Demo unlocked' : 'Empty'}</Badge></div><div className="card-bottom"><span>UI state only · no keys loaded</span><button className="text-button" onClick={() => vault?.state === 'locked' ? setDialog('unlock') : navigate('vault')}>{vault?.state === 'locked' ? 'Preview unlock' : 'Manage vault'}<ArrowRight size={14} aria-hidden="true" /></button></div></section>}
      <section className="card algorithm-summary"><div className="section-heading"><h2>Two layers. One signature pair.</h2><Fingerprint size={19} aria-hidden="true" /></div><div className="algorithm-flow"><span><span className="algorithm-number">01</span><strong>Ed25519</strong><small>First signature</small></span><ArrowRight size={18} aria-hidden="true" /><span><span className="algorithm-number">02</span><strong>Falcon-512</strong><small>Signs the next state</small></span><ShieldCheck size={24} className="algorithm-shield" aria-hidden="true" /></div><p>The Python verifier requires both layers to be valid. This UI does not run it yet.</p></section>
    </div>
    <section className="card activity-card"><div className="section-heading"><div className="heading-with-caption"><h2>Recent activity</h2><span>This preview session</span></div>{activities.length > 0 ? <button className="text-button" onClick={clearActivity}>Clear activity</button> : <Badge>SESSION ONLY</Badge>}</div>
      {activities.length === 0 ? <div className="empty-activity"><span className="empty-stack"><Files size={26} strokeWidth={1.4} aria-hidden="true" /></span><div><h3>A fresh start for your documents</h3><p>Your UI-preview activity will appear here. No documents have been processed.</p></div><ArrowDown size={17} className="empty-arrow" aria-hidden="true" /></div> : <ul className="activity-list">{activities.map(item => <li key={item.id}><IconTile icon={item.type === 'sign' ? FilePenLine : item.type === 'verify' ? ShieldCheck : LockKeyhole} small /><div><strong>{item.title}</strong><p>{item.detail}</p></div><Badge>UI PREVIEW</Badge><time dateTime={new Date(item.at).toISOString()}><Clock3 size={12} aria-hidden="true" />{new Date(item.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time></li>)}</ul>}
    </section>
  </div>
}
