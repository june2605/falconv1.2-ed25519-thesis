import { ArrowLeft, ArrowRight, Download, FilePenLine, Info, LockKeyhole } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { DocumentSelection, SigningPreview } from '../models'
import { usePreviewTask } from '../hooks'
import { useWorkspace } from '../state/workspace'
import { demoService, downloadPreviewSummary } from '../services/demo'
import { DocumentPicker } from '../components/DocumentPicker'
import { DocumentPreview } from '../components/DocumentPreview'
import { Badge, Button, DetailsRow, IconTile, Notice, PageHeader } from '../components/ui'
import { WorkflowStep } from '../components/WorkflowStep'
import { TaskFooter } from '../components/TaskFooter'
import { useDesktopConnection } from '../native/status'
import { useNativeSigning } from '../native/signing'
import { NativeSignDocument } from './NativeSignDocument'

export function SignDocument() {
  return useNativeSigning().integrated ? <NativeSignDocument /> : <DemoSignDocument />
}

function DemoSignDocument() {
  const [document, setDocument] = useState<DocumentSelection | null>(null)
  const [step, setStep] = useState(1)
  const previousStep = useRef(step)
  const { vault, setDialog, addActivity } = useWorkspace()
  const desktop = useDesktopConnection().mode === 'desktop'
  const task = usePreviewTask<SigningPreview>()
  const ready = !!document && vault?.state === 'unlocked'
  useEffect(() => {
    if (previousStep.current !== step) {
      const heading = window.document.getElementById(`sign-step-${step}`)
      heading?.focus({ preventScroll: true }); heading?.scrollIntoView({ block: 'nearest' })
      previousStep.current = step
    }
  }, [step])
  function changeDocument(value: DocumentSelection | null) { setDocument(value); task.reset(); setStep(value ? 2 : 1) }
  return <>
    <PageHeader title="Sign a document" description="Choose a PDF, select your vault, then review." />
    <div className="workflow-grid"><section className="card workflow-card" aria-label="Signing workflow">
      <div className="workflow-intro"><span>STEP {step} OF 3</span><span>Ed25519 <ArrowRight size={13} aria-hidden="true" /> Falcon-512</span></div>
      <WorkflowStep number={1} title="Choose PDF" active={step === 1} complete={!!document} summary={document?.name} disabled={task.busy} onSelect={() => setStep(1)}><DocumentPicker value={document} onChange={changeDocument} disabled={task.busy} /></WorkflowStep>
      <WorkflowStep number={2} title="Select vault" active={step === 2} complete={vault?.state === 'unlocked' && !!document} summary={vault ? `${vault.name} · ${vault.state === 'locked' ? 'locked' : 'demo unlocked'}` : 'No demo vault'} disabled={!document || task.busy} onSelect={() => setStep(2)}>
        <div className="selected-vault"><IconTile icon={LockKeyhole} small /><div><strong>{vault?.name ?? 'No demo vault'}</strong><span>Ed25519 + Falcon-512</span></div><Badge tone={vault?.state === 'unlocked' ? 'indigo' : 'neutral'}>{vault?.state === 'unlocked' ? 'Demo unlocked' : vault ? 'Locked' : 'Empty'}</Badge></div>
        <p className="step-description">{vault?.state === 'unlocked' ? 'Demo state only. No private keys are loaded.' : 'Preview an unlocked vault to continue. No password is requested.'}</p>
        {vault && <button className="text-button" onClick={() => setDialog('public')}>Public key details<ArrowRight size={14} aria-hidden="true" /></button>}
      </WorkflowStep>
      <WorkflowStep number={3} title="Review and sign" active={step === 3} disabled={!ready || task.busy} onSelect={() => setStep(3)}>
        <dl className="review-details"><DetailsRow label="Document">{document?.name}</DetailsRow><DetailsRow label="Demo vault">{vault?.name}</DetailsRow><DetailsRow label="Sequence">Ed25519 → Falcon-512</DetailsRow></dl>
        <Notice title="PDF signing is unavailable in this preview">Try the workflow and download a JSON summary of the preview.</Notice>
      </WorkflowStep>
      {task.error && <div className="result-area"><Notice tone="error" title="Preview could not complete">{task.error}</Notice></div>}
      {task.result && <div className="result-area" role="status"><div className="result-heading"><Info size={20} aria-hidden="true" /><h2>Signing workflow previewed</h2><Badge tone="indigo">DEMO</Badge></div><p>No PDF was signed or changed.</p><Button variant="secondary" disabled={desktop} onClick={() => downloadPreviewSummary(task.result!)}><Download size={15} aria-hidden="true" />Download preview summary</Button><small>{desktop ? 'Native downloads are disabled in this desktop phase.' : 'JSON only · not a signed document'}</small></div>}
    </section><DocumentPreview document={document} /></div>
    <TaskFooter label="Signing actions" title={step === 1 ? 'Choose a PDF to begin' : step === 2 ? 'Next: select your vault' : 'Review complete · demo only'} description={<span id="sign-unavailable">Use a desktop build with signing support to sign this PDF.</span>}>
      {step > 1 && <Button variant="ghost" disabled={task.busy} onClick={() => setStep(step - 1)}><ArrowLeft size={16} aria-hidden="true" />Back</Button>}
      {step === 1 && <Button disabled={!document} onClick={() => setStep(2)}>Continue to vault<ArrowRight size={16} aria-hidden="true" /></Button>}
      {step === 2 && (vault?.state === 'unlocked' ? <Button onClick={() => setStep(3)}>Continue to review<ArrowRight size={16} aria-hidden="true" /></Button> : <Button onClick={() => setDialog(vault ? 'unlock' : 'create')}><LockKeyhole size={16} aria-hidden="true" />{vault ? 'Preview unlock' : 'Create demo vault'}</Button>)}
      {step === 3 && <><Button variant="secondary" disabled={!ready} busy={task.busy} onClick={() => document && vault && void task.run(signal => demoService.sign(document, vault, signal), () => addActivity({ type: 'sign', title: 'Signing workflow previewed', detail: `${document.name} · no signed PDF created` }))}>{task.busy ? 'Previewing workflow…' : 'Preview signing'}</Button><Button disabled aria-describedby="sign-unavailable"><FilePenLine size={16} aria-hidden="true" />Sign PDF</Button></>}
    </TaskFooter>
  </>
}
