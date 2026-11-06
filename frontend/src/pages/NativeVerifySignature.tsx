import { ShieldCheck, ShieldQuestion, FileKey2, FileText, TriangleAlert } from 'lucide-react'
import { useNativeVerification } from '../native/verification'
import { useNativeSigning } from '../native/signing'
import { useNativeVault } from '../native/vault'
import { Badge, Button, DetailsRow, IconTile, Notice, PageHeader, StepHeading } from '../components/ui'
import { TaskFooter } from '../components/TaskFooter'
import { fileSize } from '../components/DocumentPicker'
import { HybridKeyId } from '../components/HybridKeyId'

export function NativeVerifySignature() {
  const verification = useNativeVerification(), signing = useNativeSigning(), { vault, busy: vaultBusy, known } = useNativeVault()
  const busy = verification.busy || signing.busy || vaultBusy
  const state = verification.job?.state
  const valid = state === 'valid' && verification.job?.hybridValid === true && !verification.uncertain
  const invalid = state === 'invalid' && verification.job?.hybridValid === false && !verification.uncertain
  const title = verification.uncertain ? 'Verification outcome not confirmed' : valid ? 'HYBRID VALID' : invalid ? 'HYBRID INVALID'
    : state === 'failed' ? 'Verification could not complete' : state === 'running' || state === 'queued' || state === 'ready' ? 'Verifying signature pair…' : 'No verification performed'
  return <>
    <PageHeader title="Verify a signature" description="Check the complete signature pair using locally selected public keys." />
    <div className="workflow-grid verify-grid"><section className="card workflow-card" aria-label="Verification workflow">
      <div className="workflow-step"><StepHeading number={1} title="Choose a signed PDF" complete={!!verification.document} />
        <p className="step-description">Choose a local PDF. Its bytes stay in Python for snapshot verification.</p>
        <Button variant="secondary" disabled={busy} onClick={() => void verification.choosePdf()}><FileText size={17} />Choose signed PDF</Button>
        {verification.document && <p className="field-hint">{verification.document.displayName} · {fileSize(verification.document.sizeBytes)}</p>}
      </div>
      <div className="workflow-step"><StepHeading number={2} title="Choose public keys" complete={!!verification.keySource} />
        <p className="step-description">Use public metadata without a password, or an authenticated vault session.</p>
        <div className="button-row"><Button variant="secondary" disabled={busy} onClick={() => void verification.chooseKeys()}><FileKey2 size={17} />Choose encrypted vault</Button>
        <Button variant="secondary" disabled={busy || !known || vault?.state !== 'unlocked' || !vault.sessionId} onClick={() => vault?.sessionId && void verification.authenticated(vault.vaultId, vault.sessionId)}>Use authenticated vault</Button></div>
        {verification.keySource && <div className="key-source-note"><FileKey2 size={18} /><div><strong>{verification.keySource.displayName}</strong><span>{verification.keySource.trust === 'vault-authenticated' ? 'Authenticated at selection' : 'Public metadata only · no password requested'}</span></div><Badge tone={verification.keySource.trust === 'vault-authenticated' ? 'success' : 'neutral'}>{verification.keySource.trust === 'vault-authenticated' ? 'LOCAL VAULT' : 'UNAUTHENTICATED'}</Badge></div>}
      </div>
      {verification.error && <div className="result-area"><Notice tone="warning">{verification.error}</Notice></div>}
    </section><aside className="verification-results"><section className="card">
      <div className="section-heading"><h2>Hybrid signature result</h2><Badge>LOCAL VERIFIER</Badge></div>
      <div className={`verification-overview ${!verification.job ? 'is-empty' : ''}`} role="status" aria-live="polite"><IconTile icon={valid ? ShieldCheck : invalid ? TriangleAlert : ShieldQuestion} tone={valid ? 'success' : 'neutral'} /><div><h2>{title}</h2><p>{valid ? 'Both signature layers are mathematically valid under the selected public-key pair.' : invalid ? 'The complete signature pair was rejected under the selected public keys. This can indicate altered bytes, a malformed signature or the wrong keys.' : 'Only a completed native check establishes an overall result. Selecting a file is not verification.'}</p></div></div>
      <div className="detail-panel-body"><dl className="public-details"><DetailsRow label="Algorithms">Ed25519 + Falcon-512</DetailsRow><DetailsRow label="Signature sequence">Ed25519 → Falcon-512</DetailsRow><DetailsRow label="Hybrid key ID">{verification.keySource ? <HybridKeyId value={verification.keySource.hybridKeyId} /> : 'Select public keys'}</DetailsRow><DetailsRow label="Individual layer status">Not exposed by this verifier</DetailsRow></dl></div>
      <div className="identity-note"><ShieldQuestion size={19} /><div><strong>Signer identity is not established</strong><p>{verification.keySource?.trust === 'vault-authenticated' ? 'The vault header was authenticated locally at key selection. This is not an identity certificate; the public snapshot remains usable after locking.' : 'Selected vault public metadata is UNAUTHENTICATED. A structurally valid header and matching key ID do not prove its origin.'} A valid PDF proves a mathematical relationship to the supplied keys, not who signed.</p></div></div>
    </section><Notice>No trusted signing time, identity registry, legal certification, CMS/PAdES or FIPS compliance is established. Verification is read-only and refers to the captured file revision.</Notice>
      {verification.uncertain && <Button variant="secondary" onClick={() => void verification.reconcile()}>Reconcile native status</Button>}
    </aside></div>
    <TaskFooter label="Verification actions" title={verification.document?.displayName ?? 'Choose a signed PDF to begin'} description="Uses the existing Python verifier. No private keys or passwords are needed.">
      <Button disabled={busy || !verification.document || !verification.keySource} onClick={() => void verification.verify()}><ShieldCheck size={17} />{state === 'failed' ? 'Retry verification' : 'Verify PDF'}</Button>
    </TaskFooter>
  </>
}
