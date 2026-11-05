import { useEffect, useRef, useState } from 'react'
import { ArrowLeft, ArrowRight, FilePenLine, FileText, LockKeyhole } from 'lucide-react'
import { useNativeSigning } from '../native/signing'
import { useNativeVault } from '../native/vault'
import { Badge, Button, DetailsRow, IconTile, Notice, PageHeader } from '../components/ui'
import { WorkflowStep } from '../components/WorkflowStep'
import { TaskFooter } from '../components/TaskFooter'
import { fileSize } from '../components/DocumentPicker'

export function NativeSignDocument() {
  const signing = useNativeSigning()
  const { vault, busy: vaultBusy, known, unlock } = useNativeVault()
  const [step, setStep] = useState(signing.document ? 2 : 1)
  const ready = !!signing.document && known && vault?.state === 'unlocked' && !!vault.sessionId
  useEffect(() => { if (signing.document && step === 1) setStep(2) }, [signing.document])
  const terminal = !!signing.job && ['completed', 'failed', 'outcome-uncertain'].includes(signing.job.state)
  const completed = signing.job?.state === 'completed' && signing.job.selfVerified
  const result = useRef<HTMLElement>(null)
  useEffect(() => { if (completed) result.current?.scrollIntoView({ block: 'center' }) }, [completed])
  const label = signing.uncertain ? 'Signing outcome not confirmed' : signing.job?.state === 'outcome-uncertain' ? 'Signing outcome uncertain'
    : signing.job?.state === 'running' ? 'Signing and self-verifying…' : signing.job?.state === 'queued' ? 'Signing queued'
    : signing.job?.state === 'ready' ? 'Choose an output location in Windows' : signing.job?.state === 'failed' ? 'Signing did not complete'
    : signing.job?.state === 'cancelled' ? 'Output selection cancelled. No signing job was queued.' : null
  return <>
    <PageHeader title="Sign a document" description="Choose a local PDF, select your unlocked vault, then review and sign." />
    <div className="workflow-grid"><section className="card workflow-card" aria-label="Signing workflow">
      <div className="workflow-intro"><span>STEP {step} OF 3</span><span>Ed25519 <ArrowRight size={13} /> Falcon-512</span></div>
      <WorkflowStep number={1} title="Choose PDF" active={step === 1} complete={!!signing.document} summary={signing.document?.displayName} disabled={signing.busy} onSelect={() => setStep(1)}>
        <p className="step-description">Choose through the Windows dialog. PDF contents stay in Python; this view shows metadata only.</p>
        <Button disabled={signing.busy} onClick={() => void signing.choose()}><FileText size={16} />Choose PDF</Button>
      </WorkflowStep>
      <WorkflowStep number={2} title="Select vault" active={step === 2} complete={ready} summary={vault ? `${vault.displayName} · ${vault.state}` : 'No vault unlocked'} disabled={!signing.document || signing.busy} onSelect={() => setStep(2)}>
        <div className="selected-vault"><IconTile icon={LockKeyhole} small /><div><strong>{vault?.displayName ?? 'No vault unlocked'}</strong><span>Ed25519 + Falcon-512</span></div><Badge>{known ? vault?.state ?? 'No session' : 'Status not confirmed'}</Badge></div>
        <p className="step-description">Only an authenticated native session can sign. Private keys remain in the Python worker.</p>
        {!ready && <Button variant="secondary" disabled={signing.busy || vaultBusy} onClick={() => void unlock()}>Unlock Vault</Button>}
      </WorkflowStep>
      <WorkflowStep number={3} title="Review and sign" active={step === 3 && !completed} complete={completed} disabled={!ready || signing.busy} onSelect={() => setStep(3)}>
        <dl><DetailsRow label="Document">{signing.document?.displayName}</DetailsRow><DetailsRow label="Vault">{vault?.displayName}</DetailsRow><DetailsRow label="Hybrid key ID"><code style={{ overflowWrap: 'anywhere' }}>{vault?.hybridKeyId}</code></DetailsRow><DetailsRow label="Sequence">Ed25519 → Falcon-512</DetailsRow></dl>
        <Notice>Sign PDF opens the native Save dialog. Existing PDF replacement requires Windows confirmation. Once queued, publication cannot be cancelled here.</Notice>
      </WorkflowStep>
      {label && <p className="field-hint" aria-live="polite">{label}</p>}
      {signing.error && <Notice tone="warning">{signing.error}</Notice>}
      {completed && <section ref={result} className="result-area" role="status"><div className="result-heading"><FilePenLine size={20} /><h2>Signed PDF saved</h2><Badge tone="success">COMPLETED</Badge></div><dl>
        <DetailsRow label="Output document">{signing.job?.outputName}</DetailsRow><DetailsRow label="Signature pair">Ed25519 + Falcon-512</DetailsRow><DetailsRow label="Self-verification">Completed self-verification</DetailsRow><DetailsRow label="Hybrid key ID"><code style={{ overflowWrap: 'anywhere' }}>{signing.job?.hybridKeyId}</code></DetailsRow></dl></section>}
      {(signing.uncertain || signing.job?.state === 'outcome-uncertain') && <Button variant="secondary" onClick={() => void signing.reconcile()}>Reconcile native status</Button>}
      {terminal && !signing.busy && <Button variant="secondary" onClick={signing.reset}>Start another signing operation</Button>}
    </section><aside className="card preview-panel"><div className="panel-header"><h2>Document workspace</h2><Badge>LOCAL FILE</Badge></div><div className="preview-empty"><FileText size={30} /><h3>{signing.document?.displayName ?? 'No PDF selected'}</h3><p>{signing.document ? fileSize(signing.document.sizeBytes) : 'Choose an unsigned PDF to begin.'}</p><p>Confirmed file metadata · PDF content is not rendered or sent to React.</p></div><Notice>Trusted signer identity and trusted signing time are not established. The PDF uses the inherited custom signature format; no CMS, PAdES or production compliance claim.</Notice></aside></div>
    <TaskFooter label="Signing actions" title={signing.busy ? 'Native signing operation active' : 'Local hybrid signing'} description="The completed pair is self-verified before atomic publication.">
      {step > 1 && <Button variant="ghost" disabled={signing.busy} onClick={() => setStep(step - 1)}><ArrowLeft size={16} />Back</Button>}
      {step === 2 && <Button disabled={!ready || signing.busy} onClick={() => setStep(3)}>Continue to review<ArrowRight size={16} /></Button>}
      <Button disabled={!ready || step !== 3 || signing.busy || terminal} onClick={() => vault?.sessionId && void signing.sign(vault.vaultId, vault.sessionId)}><FilePenLine size={16} />Sign PDF</Button>
    </TaskFooter>
  </>
}
