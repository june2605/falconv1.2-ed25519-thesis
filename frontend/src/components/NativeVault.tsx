import { useState } from 'react'
import { ArrowDownToLine, ArrowRight, CirclePlus, FileKey2, Fingerprint, HardDrive, KeyRound, LockKeyhole, ShieldCheck, UnlockKeyhole } from 'lucide-react'
import { useNativeVault } from '../native/vault'
import { HybridKeyId } from './HybridKeyId'
import { Badge, Button, DetailsRow, IconTile, Modal, Notice, PageHeader } from './ui'

export function NativeVaultSummary() {
  const { vault, busy, known, unlock } = useNativeVault()
  return <section className="card vault-summary"><div className="section-heading"><h2>Your key vault</h2><Badge tone="indigo">LOCAL VAULT</Badge></div>
    <div className="vault-summary-content"><IconTile icon={LockKeyhole} /><div><h3>{vault?.displayName ?? (known ? 'No vault unlocked' : 'Vault status unconfirmed')}</h3><p>{vault ? 'Ed25519 + Falcon-512' : 'Create or open a local encrypted vault.'}</p></div><Badge tone={vault?.state === 'unlocked' ? 'success' : 'neutral'}>{vault ? vault.state === 'unlocked' ? 'Unlocked' : 'Locked' : known ? 'Empty' : 'Unknown'}</Badge></div>
    <div className="card-bottom"><span>{!known ? 'Status not confirmed' : vault?.state === 'unlocked' ? 'Signing keys stay on this device' : 'No unlocked signing keys'}</span>{vault?.state === 'locked' ? <button className="text-button" disabled={busy} onClick={() => void unlock()}>Unlock Vault<ArrowRight size={14} /></button> : <a className="text-button" href="#/vault">Manage vault<ArrowRight size={14} /></a>}</div></section>
}

export function NativeKeyVault() {
  const { vault, busy, known, error, progress, canRetry, retry, dismissError, create, unlock, lock, refresh } = useNativeVault()
  const [details, setDetails] = useState(false)
  return <>
    <PageHeader title="Manage your signing keys" description="Create or unlock an encrypted vault. Enter the password in the Windows dialog." action={<Button disabled={busy || vault?.state === 'unlocked'} onClick={() => void create()}><CirclePlus size={17} />Create Vault</Button>} />
    {error && <Notice tone="error" title={error.title}><p>{error.message}</p><div className="button-row">
      {['vault.unlock', 'STALE_SELECTION', 'vault.conflict'].includes(error.code) && <Button variant="secondary" disabled={busy} onClick={() => void (error.code === 'vault.unlock' && canRetry ? retry() : unlock())}>{error.code === 'vault.unlock' && canRetry ? 'Try Again' : 'Select vault again'}</Button>}
      <Button variant="ghost" aria-label={error.code === 'vault.unlock' ? 'Dismiss unlock error' : 'Dismiss vault error'} onClick={dismissError}>Dismiss</Button>
    </div></Notice>}
    {progress && <p className="field-hint" aria-live="polite" data-vault-progress>{progress}</p>}
    <div className="vault-grid"><section className="card vault-main">
      {vault ? <><div className="vault-card-top"><IconTile icon={vault.state === 'locked' ? LockKeyhole : UnlockKeyhole} tone="indigo" /><Badge tone="indigo">LOCAL VAULT</Badge></div>
        <div className="vault-overview"><div><h2 className="vault-name">{vault.displayName}</h2><p className="vault-subtitle">Ed25519 + Falcon-512</p></div><div className="vault-primary-actions">{vault.state === 'locked' ? <Button busy={busy} onClick={() => void unlock()}><UnlockKeyhole size={16} />Unlock Vault</Button> : <Button variant="secondary" busy={busy} onClick={() => void lock()}><LockKeyhole size={16} />Lock Vault</Button>}</div></div>
        <div className="vault-status-line"><Badge tone={vault.state === 'unlocked' ? 'success' : 'neutral'}>{vault.state === 'unlocked' ? 'Unlocked' : 'Locked'}</Badge><span>{vault.state === 'unlocked' ? 'Private keys stay on this device' : 'Public keys from the last confirmed vault session'}</span></div>
        <div className="vault-id"><span className="field-label">Hybrid key ID</span><HybridKeyId value={vault.hybridKeyId} /><span className="field-hint">Identifies the public-key pair. Confirm it with a trusted source.</span></div>
        <section className="vault-management" aria-label="Vault management"><h3>Manage vault</h3><div className="vault-tool-actions"><Button variant="secondary" onClick={() => setDetails(true)}><FileKey2 size={16} />Public key details</Button><Button variant="secondary" disabled><KeyRound size={16} />Change password</Button><Button variant="secondary" disabled><ArrowDownToLine size={16} />Encrypted backup</Button><Button variant="secondary" disabled>Restore a vault<ArrowRight size={15} /></Button></div></section>
      </> : <div className="vault-empty"><IconTile icon={LockKeyhole} tone="indigo" /><h2>{busy ? progress : known ? 'No vault unlocked' : 'Vault status unconfirmed'}</h2><p>Create a new encrypted vault or unlock an existing one. Choose its location and enter the password in Windows dialogs.</p><Button busy={busy} onClick={() => void unlock()}><UnlockKeyhole size={16} />Unlock Vault</Button></div>}
      <div className="button-row"><Button variant="ghost" disabled={busy} onClick={() => void refresh()}>Refresh status</Button>{vault?.state === 'locked' && <Button variant="ghost" disabled={busy} onClick={() => void unlock()}>Open another vault</Button>}</div>
      <p className="field-hint">Password changes, backup and restore are unavailable in this version.</p>
    </section><aside className="vault-side"><section className="card"><div className="section-heading"><h2>Security information</h2><ShieldCheck size={19} /></div><ul className="security-list"><li><HardDrive size={18} /><div><strong>Encrypted local storage</strong><p>Store the vault on a fixed local NTFS drive with access limited to your Windows account.</p></div></li><li><LockKeyhole size={18} /><div><strong>Windows password prompt</strong><p>Passwords and private keys stay on this device. Locking ends access for signing, but cannot guarantee that every copy in memory is removed.</p></div></li><li><Fingerprint size={18} /><div><strong>Identity is separate</strong><p>Trusted signer identity is not established.</p></div></li></ul></section><Notice title="Keep your vault and password">You need the encrypted file and its password to use these keys again. HybridSign cannot recover a forgotten password.</Notice></aside></div>
    <Modal open={details && !!vault} onOpenChange={setDetails} title="Public key details" description="Public keys from your vault. Confirm the key ID through a trusted source." label="LOCAL VAULT"><dl className="public-details"><DetailsRow label="Vault">{vault?.displayName}</DetailsRow><DetailsRow label="Hybrid key ID">{vault && <HybridKeyId value={vault.hybridKeyId} />}</DetailsRow><DetailsRow label="Ed25519 public key"><code style={{ overflowWrap: 'anywhere' }}>{vault?.ed25519PublicKey}</code></DetailsRow><DetailsRow label="Falcon-512 public key"><code style={{ overflowWrap: 'anywhere' }}>{vault?.falconPublicKey}</code></DetailsRow><DetailsRow label="Vault format">Version {vault?.formatVersion} · 2416 bytes</DetailsRow><DetailsRow label="Trusted identity">Not established</DetailsRow></dl></Modal>
  </>
}
