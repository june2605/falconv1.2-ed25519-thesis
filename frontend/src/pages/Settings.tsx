import { Check, ChevronDown, ChevronRight, Globe2, Monitor, Moon, SlidersHorizontal, Sun } from 'lucide-react'
import type { Appearance } from '../models'
import { useWorkspace } from '../state/workspace'
import { Badge, Button, PageHeader } from '../components/ui'
import { useNativeVault } from '../native/vault'
import { useNativeSigning } from '../native/signing'
import { useNativeVerification } from '../native/verification'

const themes = [{ value: 'light', label: 'Light', icon: Sun }, { value: 'dark', label: 'Dark', icon: Moon }, { value: 'system', label: 'System', icon: Monitor }] as const

export function Settings() {
  const { appearance, setAppearance, reducedMotion, setReducedMotion, setDialog, reset } = useWorkspace()
  const { integrated } = useNativeVault()
  const signing = useNativeSigning().integrated
  const verifying = useNativeVerification().integrated
  return <>
    <PageHeader title="Settings" description="Manage appearance, motion and language." />
    <div className="settings-layout"><div className="settings-main"><section className="card settings-card"><div className="section-heading"><div><h2>Appearance</h2><p>Choose a color theme.</p></div><SlidersHorizontal size={19} aria-hidden="true" /></div><fieldset className="theme-options"><legend className="sr-only">Color theme</legend>{themes.map(({ value, label, icon: Icon }) => <label className={`theme-choice ${appearance === value ? 'selected' : ''}`} key={value}><input type="radio" name="appearance" value={value} checked={appearance === value} onChange={event => setAppearance(event.target.value as Appearance)} /><div className={`theme-mini theme-mini-${value}`} aria-hidden="true"><i /><span><b /><b /><b /></span><div /></div><span className="theme-choice-label"><Icon size={16} aria-hidden="true" />{label}{appearance === value && <Check size={15} className="theme-check" aria-hidden="true" />}</span></label>)}</fieldset><div className="setting-row"><div><h3>Reduce motion</h3><p>Reduce animations and transitions.</p></div><button role="switch" aria-label="Reduce motion" aria-checked={reducedMotion} className="switch" onClick={() => setReducedMotion(!reducedMotion)}><span /></button></div></section>
      <section className="card settings-card"><div className="setting-row"><div className="setting-with-icon"><Globe2 size={20} aria-hidden="true" /><div><h2>Language</h2><p>The interface is available in English.</p></div></div><button className="button button-secondary" onClick={() => setDialog('language')}>English<ChevronRight size={15} aria-hidden="true" /></button></div></section>
      <section className="card settings-card"><div className="setting-row"><div><h2>Reset UI preview</h2><p>Clear demo vault and session activity.</p></div><Button variant="secondary" onClick={reset}>Reset preview</Button></div><p className="settings-footnote">Reloading resets preferences and demo data.</p></section>
    </div><aside className="card about-card"><div className="about-brand"><img src="./mark.svg" alt="" width="36" height="36" /><div><h2>HybridSign</h2><Badge>Version 0.1.0</Badge></div></div><p>PDF signatures with Ed25519 and Falcon-512.</p><Button variant="secondary" onClick={() => setDialog('about')}>About and limitations<ChevronRight size={15} aria-hidden="true" /></Button><details className="about-limitations"><summary>Research limitations<ChevronDown size={16} aria-hidden="true" /></summary><ul><li>{verifying ? 'Verification checks both signatures against the selected public keys.' : signing ? 'Signing checks both signatures before saving.' : integrated ? 'This version provides vault management only.' : 'Example results are available in the browser preview.'}</li><li>Signer identity and signing time require separate evidence.</li><li>HybridSign uses a custom PDF signature format.</li></ul></details></aside></div>
  </>
}
