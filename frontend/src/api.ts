import type { ExplainResponse, Language } from './types'

// Where the backend lives. In development it is the local uvicorn server. In a
// production build it defaults to "" (same domain), which is how the Vercel
// deployment serves both the website and /api. VITE_API_BASE_URL overrides both.
export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '')
).replace(/\/+$/, '')

// Shown in error messages; "" means this website's own domain.
const SERVER_LABEL = API_BASE_URL || 'this website'

// Same limits the backend enforces (backend/app/main.py and backend/app/pdf_extraction.py).
export const MAX_TEXT_LENGTH = 20_000
export const MAX_PDF_BYTES = 4 * 1024 * 1024
export const PDF_LIMIT_TEXT = '4 MB'

/** An error whose message is safe to show to the user. */
export class ApiError extends Error {}

interface ValidationIssue {
  msg?: string
}

async function describeError(response: Response): Promise<string> {
  try {
    const body = await response.json()
    // HTTPException errors (e.g. from /api/process-pdf) send a plain message.
    if (typeof body.detail === 'string' && body.detail) {
      return body.detail
    }
    if (response.status === 422 && Array.isArray(body.detail)) {
      const messages = (body.detail as ValidationIssue[])
        .map((issue) => (issue.msg ?? '').replace(/^Value error, /, ''))
        .filter(Boolean)
      if (messages.length) {
        return `The server could not accept this input: ${messages.join('; ')}.`
      }
    }
  } catch {
    // Response was not JSON; fall through to the generic message.
  }
  return `The server returned an error (HTTP ${response.status}). Please try again.`
}

async function post(path: string, init: RequestInit): Promise<ExplainResponse> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { method: 'POST', ...init })
  } catch {
    throw new ApiError(
      `Could not reach the Samjho server at ${SERVER_LABEL}. ` +
        'Make sure the backend is running and try again.',
    )
  }
  if (!response.ok) {
    throw new ApiError(await describeError(response))
  }
  return (await response.json()) as ExplainResponse
}

export function explainDocument(text: string, language: Language): Promise<ExplainResponse> {
  return post('/api/explain', {
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, language }),
  })
}

export function explainPdf(file: File, language: Language): Promise<ExplainResponse> {
  const form = new FormData()
  form.append('file', file)
  form.append('language', language)
  // No Content-Type header: the browser sets the multipart boundary itself.
  return post('/api/process-pdf', { body: form })
}
