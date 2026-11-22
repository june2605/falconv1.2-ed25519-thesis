import { useState } from 'react'
import { CheckCircle2, ChevronDown, Download, FileKey2, ShieldCheck, ShieldQuestion, TriangleAlert, XCircle } from 'lucide-react'
import type { DocumentSelection, ExampleCheck, VerificationPreview, VerificationScenario } from '../models'
import { usePreviewTask } from '../hooks'
import { demoService, downloadPreviewSummary } from '../services/demo'
import { useWorkspace } from '../state/workspace'
import { DocumentPicker } from '../components/DocumentPicker'
import { Badge, Button, DetailsRow, IconTile, Notice, PageHeader, StepHeading } from '../components/ui'
import { TaskFooter } from '../components/TaskFooter'
import { useDesktopConnection } from '../native/status'
import { useNativeVerification } from '../native/verification'
import { NativeVerifySignature } from './NativeVerifySignature'

const scenarios: { id: VerificationScenario; label: string }[] = [
  { id: 'both-valid', label: 'Both layers pass (example)' }, { id: 'altered', label: 'Document altered (example)' },
  { id: 'ed25519-fails', label: 'Ed25519 fails (example)' }, { id: 'falcon-fails', label: 'Falcon-512 fails (example)' }, { id: 'error', label: 'Cannot read signature (example)' },
]

function Layer({ name, subtitle, state }: { name: string; subtitle: string; state?: ExampleCheck }) {
  const Icon = state === 'example-pass' ? CheckCircle2 : state === 'example-fail' ? XCircle : ShieldQuestion
  return <div className={`verification-layer ${state ?? ''}`}><div className="layer-title"><Icon size={21} aria-hidden="true" /><h3>{name}</h3></div><p>{subtitle}</p><Badge tone={state === 'example-pass' ? 'success' : state === 'example-fail' ? 'error' : 'neutral'}>{state === 'example-pass' ? 'Example: pass' : state === 'example-fail' ? 'Example: fail' : state === 'not-run' ? 'Example: not run' : 'Awaiting preview'}</Badge></div>
}

export function VerifySignature() {
  const native = useNativeVerification().integrated
  const desktop = useDesktopConnection().mode === 'desktop'
  if (native) return <NativeVerifySignature />
  if (desktop) return <><PageHeader title="Verify a signature" description="Verification is unavailable in this version of HybridSign." /><Notice>Use a desktop build that supports verification. The browser preview shows example results.</Notice><TaskFooter label="Verification actions" title="Verification unavailable" description="No verification has been performed."><Button disabled>Verify PDF</Button></TaskFooter></>
  return <DemoVerifySignature />
}

function DemoVerifySignature() {
  const [document, setDocument] = useState<DocumentSelection | null>(null)
  const [scenario, setScenario] = useState<VerificationScenario>('both-valid')
  const [keySource, setKeySource] = useState('demo')
  const [keyFiles, setKeyFiles] = useState({ ed25519: '', falcon: '' })
  const task = usePreviewTask<VerificationPreview>()
  const { addActivity } = useWorkspace()
  const desktop = useDesktopConnection().mode === 'desktop'
  const bothPass = task.result?.ed25519 === 'example-pass' && task.result.falcon === 'example-pass'
  const cannotRead = task.result?.scenario === 'error'
  const ready = !!document && (keySource === 'demo' || !!keyFiles.ed25519 && !!keyFiles.falcon)
  function changeDocument(value: DocumentSelection | null) { setDocument(value); task.reset() }
  return <>
    <PageHeader title="Verify a signature" description="Choose a signed PDF and its matching public keys." />
    <div className="workflow-grid verify-grid"><section className="card workflow-card" aria-label="Verification workflow">
      <div className="workflow-step"><StepHeading number={1} title="Choose a signed PDF" complete={!!document} /><DocumentPicker value={document} onChange={changeDocument} disabled={task.busy} /></div>
      <div className="workflow-step"><StepHeading number={2} title="Choose public keys" /><label className="field-label" htmlFor="key-source">Public-key source</label><select id="key-source" value={keySource} disabled={task.busy} onChange={event => { setKeySource(event.target.value); task.reset() }}><option value="demo">Demo key pair · UI placeholder</option><option value="files">Choose public-key files · metadata only</option></select>
        {keySource === 'demo' ? <div className="key-source-note"><FileKey2 size={18} aria-hidden="true" /><div><strong>Ed25519 + Falcon-512</strong><span>No real public keys are loaded.</span></div><Badge>DEMO</Badge></div> : <div className="key-file-fields">{(['ed25519', 'falcon'] as const).map(key => <div key={key}><label className="field-label" htmlFor={`${key}-public-file`}>{key === 'ed25519' ? 'Ed25519 public key' : 'Falcon-512 public key'}</label><input id={`${key}-public-file`} type="file" aria-describedby={`${key}-file-hint`} disabled={task.busy} onChange={event => { setKeyFiles(current => ({ ...current, [key]: event.target.files?.[0]?.name ?? '' })); task.reset() }} /><span id={`${key}-file-hint`} className="field-hint">{keyFiles[key] || 'Select a public-key file. Contents will not be read.'}</span></div>)}</div>}
      </div>
      {task.error && <div className="result-area"><Notice tone="error">{task.error}</Notice></div>}
    </section>
    <aside className="verification-results"><section className="card"><div className="section-heading"><h2>Signature layers</h2>{task.result && <Badge tone="indigo">EXAMPLE</Badge>}</div><div className={`verification-overview ${!task.result ? 'is-empty' : ''}`}><IconTile icon={task.result ? bothPass ? ShieldCheck : TriangleAlert : ShieldQuestion} tone={bothPass ? 'success' : 'neutral'} /><div><h2>{!task.result ? 'No verification performed' : cannotRead ? 'Example: unable to verify' : bothPass ? 'Example: both layers pass' : 'Example: signature rejected'}</h2><p>{!task.result ? 'This browser preview shows example results.' : 'Illustrative result only. No cryptographic verification was performed.'}</p></div></div><div className="verification-layers"><Layer name="Ed25519" subtitle="First signature layer" state={task.result?.ed25519} /><Layer name="Falcon-512" subtitle="Second signature layer" state={task.result?.falcon} /></div><div className="identity-note"><ShieldQuestion size={19} aria-hidden="true" /><div><strong>Signer identity is not established</strong><p>Signer identity needs a separate, trusted link to the public keys.</p></div></div></section>
      <details className="card example-controls"><summary>Explore example results<ChevronDown size={17} aria-hidden="true" /></summary><div className="detail-panel-body"><label className="field-label" htmlFor="scenario">Example scenario</label><select id="scenario" value={scenario} disabled={task.busy} onChange={event => { setScenario(event.target.value as VerificationScenario); task.reset() }}>{scenarios.map(item => <option value={item.id} key={item.id}>{item.label}</option>)}</select><p className="field-hint">DEMO · selected examples, not checks of your PDF.</p><Button variant="secondary" busy={task.busy} disabled={!ready} onClick={() => document && void task.run(signal => demoService.verify(document, scenario, signal), () => addActivity({ type: 'verify', title: 'Verification result previewed', detail: `${document.name} · illustrative results only` }))}><ShieldCheck size={17} aria-hidden="true" />{task.busy ? 'Loading example…' : 'Preview verification'}</Button></div></details>
      <details className="card detail-panel"><summary>Result details <ChevronDown size={17} aria-hidden="true" /></summary><div className="detail-panel-body"><dl><DetailsRow label="Execution">UI preview · no cryptography</DetailsRow><DetailsRow label="Signature sequence">Ed25519 → Falcon-512</DetailsRow><DetailsRow label="Trusted identity">Not established</DetailsRow><DetailsRow label="Authenticated signing time">Not available</DetailsRow><DetailsRow label="Key registry">Not connected</DetailsRow><DetailsRow label="PDF compliance">No CMS or PAdES claim</DetailsRow></dl>{task.result && <><Button variant="secondary" disabled={desktop} onClick={() => downloadPreviewSummary(task.result!)}><Download size={15} aria-hidden="true" />Download preview summary</Button>{desktop && <p className="field-hint">Preview downloads are available in the browser.</p>}</>}</div></details>
    </aside></div>
    <TaskFooter label="Verification actions" title={document ? document.name : 'Choose a signed PDF to begin'} description={<span id="verify-unavailable">Use the desktop app to verify this PDF.</span>}><Button disabled aria-describedby="verify-unavailable"><ShieldCheck size={17} aria-hidden="true" />Verify PDF</Button></TaskFooter>
  </>
}
