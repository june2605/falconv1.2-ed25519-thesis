import { FileText, FileUp, FolderOpen, Upload, X } from 'lucide-react'
import { useEffect, useId, useRef, useState, type DragEvent } from 'react'
import type { DocumentSelection } from '../models'
import { sampleDocument, selectPdf } from '../services/demo'
import { Badge, Button, Notice } from './ui'

export function fileSize(size: number): string { return size < 1024 * 1024 ? `${(size / 1024).toFixed(0)} KiB` : `${(size / 1024 / 1024).toFixed(1)} MiB` }

export function DocumentPicker({ value, onChange, disabled = false }: { value: DocumentSelection | null; onChange: (value: DocumentSelection | null) => void; disabled?: boolean }) {
  const input = useRef<HTMLInputElement>(null)
  const id = useId()
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')
  const [reading, setReading] = useState(false)
  const selection = useRef(0)
  useEffect(() => () => { ++selection.current }, [])
  async function accept(files: FileList | null) {
    const active = ++selection.current
    setError('')
    if (!files?.length) return
    if (files.length !== 1) { setError('Choose one PDF document at a time.'); return }
    setReading(true)
    try { const value = await selectPdf(files[0]); if (selection.current === active) onChange(value) }
    catch (cause) { if (selection.current === active) setError(cause instanceof Error ? cause.message : 'Could not read this selection.') }
    finally { if (selection.current === active) { setReading(false); if (input.current) input.current.value = '' } }
  }
  function drop(event: DragEvent) {
    event.preventDefault(); setDragging(false)
    if (!disabled && !reading) void accept(event.dataTransfer.files)
  }
  return <div className="document-picker">
    <input ref={input} id={id} className="sr-only" tabIndex={-1} type="file" accept=".pdf,application/pdf" aria-label="Choose PDF document" disabled={disabled || reading}
      onChange={event => void accept(event.currentTarget.files)} />
    {value ? <div className="selected-document"><span className="pdf-file-icon" aria-hidden="true"><FileText size={23} /><small>PDF</small></span><div className="file-description"><strong title={value.name}>{value.name}</strong><span>{fileSize(value.size)} <span aria-hidden="true">·</span> {value.source === 'sample' ? 'Illustrative sample' : 'Selected locally'}</span></div>
      {value.source === 'sample' && <Badge tone="indigo">DEMO</Badge>}<button className="icon-button" aria-label="Remove selected document" disabled={disabled} onClick={() => { onChange(null); setError('') }}><X size={17} /></button></div>
      : <div className={`dropzone ${dragging ? 'dragging' : ''} ${disabled ? 'disabled' : ''}`}
        onDragOver={event => { event.preventDefault(); if (!disabled) setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={drop}>
        <span className="upload-icon"><FileUp size={25} strokeWidth={1.5} aria-hidden="true" /><span><Upload size={10} /></span></span>
        <strong>Drop a PDF here</strong><span>PDF only, up to 50 MiB</span>
        <Button variant="secondary" busy={reading} disabled={disabled} onClick={() => input.current?.click()}><FolderOpen size={15} />Choose PDF</Button>
      </div>}
    {!value && <button className="text-button sample-button" disabled={disabled || reading} onClick={() => { setError(''); onChange({ ...sampleDocument }) }}>Just exploring? Use a sample document <span aria-hidden="true">↗</span></button>}
    {error && <Notice tone="error">{error}</Notice>}
  </div>
}
