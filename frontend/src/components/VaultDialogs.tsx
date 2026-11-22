import { useState } from 'react'
import { ArrowDownToLine, ArrowRight, FileKey2, Info, KeyRound, LockKeyhole } from 'lucide-react'
import { useWorkspace } from '../state/workspace'
import { usePreviewTask } from '../hooks'
import { demoService, initialDemoVault } from '../services/demo'
import { requireNativeBridge } from '../native/contracts'
import type { VaultDialog } from '../models'
import { useDesktopConnection } from '../native/status'
import { useNativeVault } from '../native/vault'
import { useNativeSigning } from '../native/signing'
import { useNativeVerification } from '../native/verification'
import { Badge, Button, DetailsRow, Modal, Notice } from './ui'

const labels: Record<VaultDialog, { title: string; description: string }> = {
  create: { title: 'Create a demo vault', description: 'Give the demo vault a name for this session.' },
  unlock: { title: 'Preview vault unlock', description: 'Try the unlocked view with demo data.' },
  password: { title: 'Preview a password change', description: 'Password changes are unavailable in HybridSign 0.1.0.' },
  backup: { title: 'Preview a backup', description: 'Encrypted backup export is unavailable in HybridSign 0.1.0.' },
  restore: { title: 'Preview a restore', description: 'This preview uses demo data. Open an existing vault file in the desktop app to use its keys.' },
  public: { title: 'Public key details', description: 'These are example values. Actual keys appear in the desktop Key Vault.' },
  clear: { title: 'Clear the demo vault?', description: 'Clear the demo card for this session. Vault files stay on disk.' },
  about: { title: 'About HybridSign', description: 'A Windows research app for signing and verifying PDFs with Ed25519 and Falcon-512.' },
  language: { title: 'Language preferences', description: 'English is the only available language.' },
}

export function VaultDialogs() {
  const { dialog, setDialog } = useWorkspace()
  return dialog ? <VaultDialogContent key={dialog} type={dialog} onClose={() => setDialog(null)} /> : null
}

function VaultDialogContent({ type, onClose }: { type: VaultDialog; onClose: () => void }) {
  const { vault, setVault, notify, addActivity } = useWorkspace()
  const desktop = useDesktopConnection().mode === 'desktop'
  const { integrated } = useNativeVault()
  const signing = useNativeSigning().integrated
  const verifying = useNativeVerification().integrated
  const [name, setName] = useState('')
  const [nameError, setNameError] = useState('')
  const task = usePreviewTask<void>()
  function nativeRequest() {
    try { requireNativeBridge() } catch (error) { notify(integrated ? 'Signing workflow is still a demo' : desktop ? 'Vault integration unavailable' : 'Desktop action unavailable here', integrated ? 'Use Key Vault for real local vault operations. No PDF operation was performed.' : desktop ? 'Only desktop status is connected. No vault operation was performed.' : error instanceof Error ? error.message : 'No operation was performed.', 'info') }
  }
  function preview(action: 'create' | 'unlock' | 'restore' | 'backup' | 'password') {
    if (action === 'create' && (name.trim().length < 3 || name.trim().length > 40 || /[\x00-\x1f\x7f]/.test(name))) { setNameError('Enter a name with 3 to 40 characters and no control characters.'); return }
    void task.run(signal => demoService.vaultAction(action === 'create' ? name : action, signal), () => {
      if (action === 'create') setVault({ ...initialDemoVault(), name: name.trim() })
      if (action === 'unlock' && vault) setVault({ ...vault, state: 'unlocked' })
      if (action === 'restore') setVault({ ...initialDemoVault(), name: 'Restored demo vault' })
      const title = action === 'unlock' ? 'Demo vault unlocked' : action === 'create' ? 'Demo vault created' : action === 'restore' ? 'Restore flow previewed' : action === 'backup' ? 'Backup flow previewed' : 'Password change previewed'
      addActivity({ type: 'vault', title, detail: 'UI preview only · no keys, passwords or files changed' })
      notify(title, action === 'backup' ? 'No backup file was created.' : 'UI state only. No real vault operation was performed.')
      onClose()
    })
  }
  const infoOnly = ['public', 'about', 'language'].includes(type)
  const footer = infoOnly ? <Button variant="secondary" onClick={onClose}>Done</Button> : type === 'clear' ? <><Button variant="secondary" onClick={onClose}>Cancel</Button><Button variant="danger" onClick={() => { setVault(null); onClose(); notify('Demo vault cleared', 'No files were deleted.') }}>Clear demo vault</Button></> : <><Button variant="secondary" onClick={onClose}>Cancel</Button><Button busy={task.busy} disabled={type === 'unlock' && !vault} onClick={() => preview(type as 'create' | 'unlock' | 'restore' | 'backup' | 'password')}>{type === 'create' ? 'Create demo vault' : type === 'unlock' ? 'Preview unlocked state' : type === 'restore' ? 'Preview restored state' : 'Preview completion'}<ArrowRight size={15} aria-hidden="true" /></Button></>
  return <Modal open onOpenChange={open => !open && onClose()} {...labels[type]} description={integrated && type === 'unlock' ? 'Use Key Vault to unlock an encrypted vault. This signing preview uses demo data.' : labels[type].description} icon={type === 'unlock' ? LockKeyhole : type === 'password' ? KeyRound : type === 'backup' ? ArrowDownToLine : type === 'public' ? FileKey2 : Info} footer={footer}>
    {type === 'create' && <form onSubmit={event => { event.preventDefault(); if (!task.busy) preview('create') }}><label className="field-label" htmlFor="vault-name">Demo vault name</label><input id="vault-name" disabled={task.busy} autoComplete="off" placeholder="e.g. Demo vault" value={name} maxLength={80} aria-invalid={!!nameError} aria-describedby={nameError ? 'vault-name-error' : 'vault-name-hint'} onChange={event => { setName(event.target.value); setNameError('') }} /><p id={nameError ? 'vault-name-error' : 'vault-name-hint'} className={nameError ? 'field-error' : 'field-hint'}>{nameError || 'Use 3 to 40 characters.'}</p></form>}
    {type === 'unlock' && <div className="native-prompt-placeholder"><LockKeyhole size={26} aria-hidden="true" /><strong>Password entry stays on your device.</strong><p>This preview never asks for your vault password.</p><Badge>{integrated ? 'Signing demo only' : 'Browser preview'}</Badge></div>}
    {['password', 'backup', 'restore'].includes(type) && <Notice title="Unavailable in this preview">{type === 'password' ? 'No password is collected here. A real change must authenticate and re-encrypt the existing vault.' : type === 'backup' ? 'A usable backup must come from the encrypted vault, not from this interface.' : 'The preview can show a restored vault card, but cannot import or unlock a real backup.'}</Notice>}
    {!infoOnly && type !== 'clear' && <div className="native-request"><span>Check desktop availability</span><button className="text-button" onClick={nativeRequest}>Check desktop support<ArrowRight size={14} aria-hidden="true" /></button></div>}
    {type === 'public' && <dl className="public-details"><DetailsRow label="Vault">{vault?.name ?? 'No demo vault'}</DetailsRow><DetailsRow label="Ed25519">Public-key size: 32 bytes</DetailsRow><DetailsRow label="Falcon-512">Public-key size: 897 bytes</DetailsRow><DetailsRow label="Hybrid key ID"><code>{vault?.keyId ?? 'Not available'}</code></DetailsRow><DetailsRow label="Key material">Not loaded in this UI preview</DetailsRow><DetailsRow label="Trusted identity">Not established</DetailsRow></dl>}
    {type === 'about' && <><div className="about-dialog-brand"><img src="./mark.svg" alt="" width="42" height="42" /><div><strong>HybridSign</strong><span>Version 0.1.0 · {desktop ? 'Desktop' : 'UI preview'}</span></div></div><Notice>{verifying ? 'Create a local vault, sign PDFs and verify both signatures with selected public keys.' : signing ? 'You can manage an encrypted vault and sign PDFs. Standalone verification is unavailable in this version.' : integrated ? 'You can create, unlock and lock a vault. Signing and verification are unavailable in this version.' : desktop ? 'Vault and PDF tools are unavailable in this version.' : 'The browser preview uses examples. Use the Windows app for actual signing and verification.'}</Notice><p className="dialog-smallprint">Signer identity and signing time require separate evidence. {integrated ? 'Vault passwords and private keys are handled on this device. Locking ends access to the keys, but other copies may remain in memory.' : 'The preview handles demo data only.'}</p></>}
    {type === 'language' && <div className="language-choice"><span>English</span><Badge tone="success">Selected</Badge></div>}
    {task.error && <Notice tone="error">{task.error}</Notice>}
  </Modal>
}
