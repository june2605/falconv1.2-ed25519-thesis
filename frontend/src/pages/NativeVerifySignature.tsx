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
  const title = verification.uncertain ? 'Verification status unconfirmed' : valid ? 'HYBRID VALID' : invalid ? 'HYBRID INVALID'
    : state === 'failed' ? 'Verification could not complete' : state === 'running' || state === 'queued' || state === 'ready' ? 'Verifying signature pair…' : 'No verification performed'
  return <>
    <PageHeader title="Verify a signature" description="Check the complete signature pair using locally selected public keys." />
    <div className="workflow-grid verify-grid"><section className="card workflow-card" aria-label="Verification workflow">
      <div className="workflow-step"><StepHeading number={1} title="Choose a signed PDF" complete={!!verification.document} />
        <p className="step-description">Choose a signed PDF to check on this device.</p>
        <Button variant="secondary" disabled={busy} onClick={() => void verification.choosePdf()}><FileText size={17} />Choose signed PDF</Button>
        {verification.document && <p className="field-hint">{verification.document.displayName} · {fileSize(verification.document.sizeBytes)}</p>}
      </div>
      <div className="workflow-step"><StepHeading number={2} title="Choose public keys" complete={!!verification.keySource} />
        <p className="step-description">Read public keys from a vault file or use the keys from an unlocked vault.</p>
        <div className="button-row"><Button variant="secondary" disabled={busy} onClick={() => void verification.chooseKeys()}><FileKey2 size={17} />Choose encrypted vault</Button>
        <Button variant="secondary" disabled={busy || !known || vault?.state !== 'unlocked' || !vault.sessionId} onClick={() => vault?.sessionId && void verification.authenticated(vault.vaultId, vault.sessionId)}>Use unlocked vault keys</Button></div>
        {verification.keySource && <div className="key-source-note"><FileKey2 size={18} /><div><strong>{verification.keySource.displayName}</strong><span>{verification.keySource.trust === 'vault-authenticated' ? 'Vault unlocked when selected' : 'Public keys read without unlocking'}</span></div><Badge tone={verification.keySource.trust === 'vault-authenticated' ? 'success' : 'neutral'}>{verification.keySource.trust === 'vault-authenticated' ? 'LOCAL VAULT' : 'UNAUTHENTICATED'}</Badge></div>}
      </div>
      {verification.error && <div className="result-area"><Notice tone="warning">{verification.error}</Notice></div>}
    </section><aside className="verification-results"><section className="card">
      <div className="section-heading"><h2>Hybrid signature result</h2><Badge>LOCAL VERIFIER</Badge></div>
      <div className={`verification-overview ${!verification.job ? 'is-empty' : ''}`} role="status" aria-live="polite"><IconTile icon={valid ? ShieldCheck : invalid ? TriangleAlert : ShieldQuestion} tone={valid ? 'success' : 'neutral'} /><div><h2>{title}</h2><p>{valid ? 'Both signatures passed with the selected public keys.' : invalid ? 'The signature pair did not pass. The file may have changed, the signature format may be invalid, or the keys may be wrong.' : 'A result appears after verification finishes.'}</p></div></div>
      <div className="detail-panel-body"><dl className="public-details"><DetailsRow label="Algorithms">Ed25519 + Falcon-512</DetailsRow><DetailsRow label="Signature sequence">Ed25519 → Falcon-512</DetailsRow><DetailsRow label="Hybrid key ID">{verification.keySource ? <HybridKeyId value={verification.keySource.hybridKeyId} /> : 'Select public keys'}</DetailsRow><DetailsRow label="Result scope">Complete signature pair</DetailsRow></dl></div>
      <div className="identity-note"><ShieldQuestion size={19} /><div><strong>Signer identity is not established</strong><p>{verification.keySource?.trust === 'vault-authenticated' ? 'You unlocked the vault when selecting these keys. They remain selected after the vault is locked.' : 'If you read keys without unlocking the vault, compare the key ID with a trusted source.'} The result applies to the keys you selected.</p></div></div>
    </section><Notice>Verification leaves the PDF unchanged and reports on the version it read. Trusted signing time and CMS or PAdES support are unverified.</Notice>
      {verification.uncertain && <Button variant="secondary" onClick={() => void verification.reconcile()}>Check verification status</Button>}
    </aside></div>
    <TaskFooter label="Verification actions" title={verification.document?.displayName ?? 'Choose a signed PDF to begin'} description="Verification uses public keys only.">
      <Button disabled={busy || !verification.document || !verification.keySource} onClick={() => void verification.verify()}><ShieldCheck size={17} />{state === 'failed' ? 'Retry verification' : 'Verify PDF'}</Button>
    </TaskFooter>
  </>
}
