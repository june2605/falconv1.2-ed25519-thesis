import { Check, ChevronDown, ChevronRight, Globe2, Monitor, Moon, SlidersHorizontal, Sun } from 'lucide-react'
import type { Appearance } from '../models'
import { useWorkspace } from '../state/workspace'
import { Badge, Button, PageHeader } from '../components/ui'
import { useNativeVault } from '../native/vault'

const themes = [{ value: 'light', label: 'Light', icon: Sun }, { value: 'dark', label: 'Dark', icon: Moon }, { value: 'system', label: 'System', icon: Monitor }] as const

export function Settings() {
  const { appearance, setAppearance, reducedMotion, setReducedMotion, setDialog, reset } = useWorkspace()
  const { integrated } = useNativeVault()
  return <>
    <PageHeader title="Personalize your workspace" description="Appearance, accessibility and application preferences." />
    <div className="settings-layout"><div className="settings-main"><section className="card settings-card"><div className="section-heading"><div><h2>Appearance</h2><p>Choose the look of your workspace.</p></div><SlidersHorizontal size={19} aria-hidden="true" /></div><fieldset className="theme-options"><legend className="sr-only">Color theme</legend>{themes.map(({ value, label, icon: Icon }) => <label className={`theme-choice ${appearance === value ? 'selected' : ''}`} key={value}><input type="radio" name="appearance" value={value} checked={appearance === value} onChange={event => setAppearance(event.target.value as Appearance)} /><div className={`theme-mini theme-mini-${value}`} aria-hidden="true"><i /><span><b /><b /><b /></span><div /></div><span className="theme-choice-label"><Icon size={16} aria-hidden="true" />{label}{appearance === value && <Check size={15} className="theme-check" aria-hidden="true" />}</span></label>)}</fieldset><div className="setting-row"><div><h3>Reduce motion</h3><p>Keep transitions and loading indicators still.</p></div><button role="switch" aria-label="Reduce motion" aria-checked={reducedMotion} className="switch" onClick={() => setReducedMotion(!reducedMotion)}><span /></button></div></section>
      <section className="card settings-card"><div className="setting-row"><div className="setting-with-icon"><Globe2 size={20} aria-hidden="true" /><div><h2>Language</h2><p>English is available in this preview.</p></div></div><button className="button button-secondary" onClick={() => setDialog('language')}>English<ChevronRight size={15} aria-hidden="true" /></button></div></section>
      <section className="card settings-card"><div className="setting-row"><div><h2>Reset UI preview</h2><p>Reset demo vault and session activity. No files are affected.</p></div><Button variant="secondary" onClick={reset}>Reset preview</Button></div><p className="settings-footnote">Preferences and demo data live in memory and reset when you reload.</p></section>
    </div><aside className="card about-card"><div className="about-brand"><img src="./mark.svg" alt="" width="36" height="36" /><div><h2>HybridSign</h2><Badge>v0.1.0 · {integrated ? 'Phase 4B.2A' : 'Phase 4A.1'}</Badge></div></div><p>Falcon–Ed25519 thesis prototype.</p><Button variant="secondary" onClick={() => setDialog('about')}>About this prototype<ChevronRight size={15} aria-hidden="true" /></Button><details className="about-limitations"><summary>Research limitations<ChevronDown size={16} aria-hidden="true" /></summary><ul><li>{integrated ? 'PDF signing and verification are not connected.' : 'Native cryptography is not connected.'}</li><li>No verified identity or trusted signing time.</li><li>No production compliance claim.</li></ul></details></aside></div>
  </>
}
