import { FileText, Maximize2 } from 'lucide-react'
import { useState } from 'react'
import type { DocumentSelection } from '../models'
import { Badge, Modal } from './ui'
import { fileSize } from './DocumentPicker'

export function PaperPreview({ selected = false, compact = false }: { selected?: boolean; compact?: boolean }) {
  return <div className={`paper-sheet ${compact ? 'paper-compact' : ''}`} aria-hidden="true"><div className="paper-mark"><span /><span /><span /></div>
    <div className="paper-eyebrow">{selected ? 'DOCUMENT WORKSPACE' : 'HYBRIDSIGN'}</div><div className="paper-title">{selected ? 'Your document' : 'Ready for your signature.'}</div>
    <div className="paper-lines"><i /><i /><i className="short" /></div><div className="paper-subtitle" /><div className="paper-lines"><i /><i /><i /><i className="short" /></div>
    <div className="paper-signature"><svg viewBox="0 0 140 40"><path d="M6 30c20-10 25-28 20-22s-6 26 5 21c16-8 14-28 8-15s-2 23 10 10 13-16 11-3 4 12 10 3 4-9 8-1 16-9 23-6 14 2 30-4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg><span /></div>
  </div>
}

export function DocumentPreview({ document }: { document: DocumentSelection | null }) {
  const [expanded, setExpanded] = useState(false)
  return <>
    <aside className="card preview-panel"><div className="panel-header"><h2>Document workspace</h2><button className="icon-button" aria-label="Expand document illustration" onClick={() => setExpanded(true)}><Maximize2 size={16} /></button></div>
      {document ? <div className="preview-canvas"><PaperPreview selected /><span className="illustration-label">ILLUSTRATIVE LAYOUT · NOT YOUR PDF</span></div> : <div className="preview-empty"><FileText size={30} strokeWidth={1.4} aria-hidden="true" /><h3>Your document workspace</h3><p>Select a PDF to view its metadata.<br />Native PDF rendering is not connected.</p></div>}
      <div className="preview-caption"><FileText size={17} aria-hidden="true" /><div><strong>{document?.name ?? 'Your PDF will appear here'}</strong><p>{document ? `${fileSize(document.size)} · file content is not rendered` : 'Select a document to begin'}</p></div></div>
    </aside>
    <Modal open={expanded} onOpenChange={setExpanded} title="Document illustration" description="This illustration is an example. The preview only displays the selected file name and size.">
      <div className="expanded-paper"><PaperPreview selected={!!document} /></div><Badge tone="indigo">PDF rendering not connected</Badge>
    </Modal>
  </>
}
