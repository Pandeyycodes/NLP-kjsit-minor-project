import { useRef, useState, type DragEvent } from 'react'
import { MAX_PDF_BYTES } from '../api'
import { formatBytes } from '../files'

interface Props {
  file: File | null
  error: string
  onSelect: (file: File | null) => void
}

export default function PdfPicker({ file, error, onSelect }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  function handleDrop(event: DragEvent) {
    event.preventDefault()
    setDragging(false)
    const dropped = event.dataTransfer.files[0]
    if (dropped) onSelect(dropped)
  }

  function clear() {
    onSelect(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <div className="field">
      <span className="field-label" id="pdf-label">
        PDF document
      </span>
      <div
        className={dragging ? 'dropzone is-dragging' : 'dropzone'}
        onDragOver={(event) => {
          event.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        data-testid="dropzone"
      >
        {file ? (
          <div className="file-row">
            <div className="file-info">
              <span className="file-name">{file.name}</span>
              <span className="file-size">{formatBytes(file.size)}</span>
            </div>
            <button type="button" className="button button-quiet" onClick={clear}>
              Remove
            </button>
          </div>
        ) : (
          <p className="dropzone-text">
            Drag a PDF here, or{' '}
            <label htmlFor="pdf-file" className="link-button">
              choose a file
            </label>
          </p>
        )}
        <input
          ref={inputRef}
          id="pdf-file"
          type="file"
          accept="application/pdf,.pdf"
          className="visually-hidden"
          aria-labelledby="pdf-label"
          aria-describedby="pdf-help"
          onChange={(event) => onSelect(event.target.files?.[0] ?? null)}
        />
      </div>
      <div id="pdf-help" className="field-help">
        {error ? (
          <span className="field-error">{error}</span>
        ) : (
          <span>
            Text-based PDFs up to {formatBytes(MAX_PDF_BYTES)}. Scanned or image-only PDFs cannot
            be read. The file is not stored.
          </span>
        )}
      </div>
    </div>
  )
}
