import { useEffect, useRef, useState } from 'react'
import { ArrowLeft, ArrowRight, FilePenLine, FileText, LockKeyhole } from 'lucide-react'
import { useNativeSigning } from '../native/signing'
import { useNativeVault } from '../native/vault'
import { Badge, Button, DetailsRow, IconTile, Notice, PageHeader } from '../components/ui'
import { WorkflowStep } from '../components/WorkflowStep'
import { TaskFooter } from '../components/TaskFooter'
import { fileSize } from '../components/DocumentPicker'
import { HybridKeyId } from '../components/HybridKeyId'

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
  const label = signing.uncertain ? 'Signing status unconfirmed' : signing.job?.state === 'outcome-uncertain' ? 'A signed PDF may already exist. Check the save location before starting again.'
    : signing.job?.state === 'running' ? 'Signing and checking the PDF…' : signing.job?.state === 'queued' ? 'Signing queued'
    : signing.job?.state === 'ready' ? 'Choose an output location in Windows' : signing.job?.state === 'failed' ? 'Signing did not complete'
    : signing.job?.state === 'cancelled' ? 'Save cancelled. Signing did not start.' : null
  return <>
    <PageHeader title="Sign a document" description="Choose a local PDF, select your unlocked vault, then review and sign." />
    <div className="workflow-grid"><section className="card workflow-card" aria-label="Signing workflow">
      <div className="workflow-intro"><span>STEP {step} OF 3</span><span>Ed25519 <ArrowRight size={13} /> Falcon-512</span></div>
      <WorkflowStep number={1} title="Choose PDF" active={step === 1} complete={!!signing.document} summary={signing.document?.displayName} disabled={signing.busy} onSelect={() => setStep(1)}>
        <p className="step-description">Choose an unsigned PDF saved on this device.</p>
        <Button disabled={signing.busy} onClick={() => void signing.choose()}><FileText size={16} />Choose PDF</Button>
      </WorkflowStep>
      <WorkflowStep number={2} title="Select vault" active={step === 2} complete={ready} summary={vault ? `${vault.displayName} · ${vault.state}` : 'No vault unlocked'} disabled={!signing.document || signing.busy} onSelect={() => setStep(2)}>
        <div className="selected-vault"><IconTile icon={LockKeyhole} small /><div><strong>{vault?.displayName ?? 'No vault unlocked'}</strong><span>Ed25519 + Falcon-512</span></div><Badge>{known ? vault?.state ?? 'No session' : 'Status not confirmed'}</Badge></div>
        <p className="step-description">Unlock a vault to use its signing keys on this device.</p>
        {!ready && <Button variant="secondary" disabled={signing.busy || vaultBusy} onClick={() => void unlock()}>Unlock Vault</Button>}
      </WorkflowStep>
      <WorkflowStep number={3} title="Review and sign" active={step === 3 && !completed} complete={completed} disabled={!ready || signing.busy} onSelect={() => setStep(3)}>
        <dl><DetailsRow label="Document">{signing.document?.displayName}</DetailsRow><DetailsRow label="Vault">{vault?.displayName}</DetailsRow><DetailsRow label="Hybrid key ID">{vault && <HybridKeyId value={vault.hybridKeyId} />}</DetailsRow><DetailsRow label="Sequence">Ed25519 → Falcon-512</DetailsRow></dl>
        <Notice>Choose where to save the signed PDF. Windows asks before replacing an existing PDF. Once HybridSign accepts the save location, wait for signing to finish.</Notice>
      </WorkflowStep>
      {label && <p className="field-hint" aria-live="polite">{label}</p>}
      {signing.error && <Notice tone="warning">{signing.error}</Notice>}
      {completed && <section ref={result} className="result-area" role="status"><div className="result-heading"><FilePenLine size={20} /><h2>Signed PDF saved</h2><Badge tone="success">COMPLETED</Badge></div><dl>
        <DetailsRow label="Output document">{signing.job?.outputName}</DetailsRow><DetailsRow label="Signature pair">Ed25519 + Falcon-512</DetailsRow><DetailsRow label="Signature check">Both signatures verified</DetailsRow><DetailsRow label="Hybrid key ID">{signing.job?.hybridKeyId && <HybridKeyId value={signing.job.hybridKeyId} />}</DetailsRow></dl></section>}
      {(signing.uncertain || signing.job?.state === 'outcome-uncertain') && <Button variant="secondary" onClick={() => void signing.reconcile()}>Check signing status</Button>}
      {terminal && !signing.busy && <Button variant="secondary" onClick={signing.reset}>Start another signing operation</Button>}
    </section><aside className="card preview-panel"><div className="panel-header"><h2>Document workspace</h2><Badge>LOCAL FILE</Badge></div><div className="preview-empty"><FileText size={30} /><h3>{signing.document?.displayName ?? 'No PDF selected'}</h3><p>{signing.document ? fileSize(signing.document.sizeBytes) : 'Choose an unsigned PDF to begin.'}</p><p>This panel shows the selected file name and size.</p></div><Notice>HybridSign uses its own PDF signature format. Signer identity and signing time need separate proof.</Notice></aside></div>
    <TaskFooter label="Signing actions" title={signing.busy ? 'Signing operation in progress' : 'Local hybrid signing'} description="HybridSign checks both signatures before saving.">
      {step > 1 && <Button variant="ghost" disabled={signing.busy} onClick={() => setStep(step - 1)}><ArrowLeft size={16} />Back</Button>}
      {step === 2 && <Button disabled={!ready || signing.busy} onClick={() => setStep(3)}>Continue to review<ArrowRight size={16} /></Button>}
      <Button disabled={!ready || step !== 3 || signing.busy || terminal} onClick={() => vault?.sessionId && void signing.sign(vault.vaultId, vault.sessionId)}><FilePenLine size={16} />Sign PDF</Button>
    </TaskFooter>
  </>
}
