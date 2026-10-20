import { MAX_PDF_BYTES, PDF_LIMIT_TEXT } from './api'

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} bytes`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/** Quick checks before upload. The backend still checks the real file contents. */
export function checkPdfFile(file: File): string | null {
  const looksLikePdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
  if (!looksLikePdf) return `“${file.name}” is not a PDF. Please choose a .pdf file.`
  if (file.size === 0) return `“${file.name}” is empty.`
  if (file.size > MAX_PDF_BYTES) {
    return `“${file.name}” (${formatBytes(file.size)}) is larger than the ${PDF_LIMIT_TEXT} limit.`
  }
  return null
}
