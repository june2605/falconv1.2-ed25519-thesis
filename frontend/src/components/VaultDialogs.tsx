import { useState } from 'react'
import { ArrowDownToLine, ArrowRight, FileKey2, Info, KeyRound, LockKeyhole } from 'lucide-react'
import { useWorkspace } from '../state/workspace'
import { usePreviewTask } from '../hooks'
import { demoService, initialDemoVault } from '../services/demo'
import { requireNativeBridge } from '../native/contracts'
import type { VaultDialog } from '../models'
import { Badge, Button, DetailsRow, Modal, Notice } from './ui'

const labels: Record<VaultDialog, { title: string; description: string }> = {
  create: { title: 'A new home for your keys', description: 'Name a demo vault to explore the interface. No key pair or encrypted vault will be created.' },
  unlock: { title: 'Unlock your signing workspace', description: 'Real vault unlocking requires a native password prompt. That connection is not implemented in this UI preview.' },
  password: { title: 'Change your vault password', description: 'In the connected application, password changes will happen through a native prompt on your device.' },
  backup: { title: 'Keep an encrypted backup', description: 'The connected application will export an encrypted vault. This preview does not create or download key material.' },
  restore: { title: 'Bring your vault with you', description: 'Restoring a real vault requires your encrypted backup and its password. Both will be handled natively in a later phase.' },
  public: { title: 'Public key details', description: 'This is demo metadata only. No public or private key material has been loaded.' },
  clear: { title: 'Clear the demo vault?', description: 'This removes the demo card from the current preview session. No files or real vaults are deleted.' },
  about: { title: 'A clearer way to sign', description: 'HybridSign is a desktop UI prototype for the Falcon–Ed25519 Hybrid Digital Signature Application.' },
  language: { title: 'Language preferences', description: 'The interface is currently available in English. More languages can be added in a future phase.' },
}

export function VaultDialogs() {
  const { dialog, setDialog } = useWorkspace()
  return dialog ? <VaultDialogContent key={dialog} type={dialog} onClose={() => setDialog(null)} /> : null
}

function VaultDialogContent({ type, onClose }: { type: VaultDialog; onClose: () => void }) {
  const { vault, setVault, notify, addActivity } = useWorkspace()
  const [name, setName] = useState('')
  const [nameError, setNameError] = useState('')
  const task = usePreviewTask<void>()
  function nativeRequest() {
    try { requireNativeBridge() } catch (error) { notify('Native connection unavailable', error instanceof Error ? error.message : 'No operation was performed.', 'info') }
  }
  function preview(action: 'create' | 'unlock' | 'restore' | 'backup' | 'password') {
    if (action === 'create' && (name.trim().length < 3 || name.trim().length > 40 || /[\x00-\x1f\x7f]/.test(name))) { setNameError('Use 3–40 characters without control characters.'); return }
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
  return <Modal open onOpenChange={open => !open && onClose()} {...labels[type]} icon={type === 'unlock' ? LockKeyhole : type === 'password' ? KeyRound : type === 'backup' ? ArrowDownToLine : type === 'public' ? FileKey2 : Info} footer={footer}>
    {type === 'create' && <form onSubmit={event => { event.preventDefault(); if (!task.busy) preview('create') }}><label className="field-label" htmlFor="vault-name">Demo vault name</label><input id="vault-name" disabled={task.busy} autoComplete="off" placeholder="e.g. Personal signing vault" value={name} maxLength={80} aria-invalid={!!nameError} aria-describedby={nameError ? 'vault-name-error' : 'vault-name-hint'} onChange={event => { setName(event.target.value); setNameError('') }} /><p id={nameError ? 'vault-name-error' : 'vault-name-hint'} className={nameError ? 'field-error' : 'field-hint'}>{nameError || 'Use 3–40 characters. This name stays in memory for this session.'}</p></form>}
    {type === 'unlock' && <div className="native-prompt-placeholder"><LockKeyhole size={26} aria-hidden="true" /><strong>Password entry stays on your device.</strong><p>This preview never asks for your vault password.</p><Badge>Native prompt not connected</Badge></div>}
    {['password', 'backup', 'restore'].includes(type) && <Notice title="Native operation not available">{type === 'password' ? 'No password is collected here. A real change must authenticate and re-encrypt the existing vault.' : type === 'backup' ? 'A usable backup must come from the encrypted vault, not from this interface.' : 'The preview can show a restored vault card, but cannot import or unlock a real backup.'}</Notice>}
    {!infoOnly && type !== 'clear' && <div className="native-request"><span>Try the future native entry point</span><button className="text-button" onClick={nativeRequest}>Request native {type === 'create' ? 'creation' : type}<ArrowRight size={14} aria-hidden="true" /></button></div>}
    {type === 'public' && <dl className="public-details"><DetailsRow label="Vault">{vault?.name ?? 'No demo vault'}</DetailsRow><DetailsRow label="Ed25519">Public-key size: 32 bytes</DetailsRow><DetailsRow label="Falcon-512">Public-key size: 897 bytes</DetailsRow><DetailsRow label="Hybrid key ID"><code>{vault?.keyId ?? 'Not available'}</code></DetailsRow><DetailsRow label="Key material">Not loaded in this UI preview</DetailsRow><DetailsRow label="Trusted identity">Not established</DetailsRow></dl>}
    {type === 'about' && <><div className="about-dialog-brand"><img src="./mark.svg" alt="" width="42" height="42" /><div><strong>HybridSign</strong><span>v0.1.0 · Phase 4A UI preview</span></div></div><Notice>The Python prototype implements Ed25519 → Falcon-512 signing. This frontend is not connected to it.</Notice><p className="dialog-smallprint">No account system, trusted signer identity, authenticated signing time or production compliance is claimed. No real signing, verification, encryption or vault operation runs in this interface.</p></>}
    {type === 'language' && <div className="language-choice"><span>English</span><Badge tone="success">Selected</Badge><p>Additional translations are not included in Phase 4A.</p></div>}
    {task.error && <Notice tone="error">{task.error}</Notice>}
  </Modal>
}
