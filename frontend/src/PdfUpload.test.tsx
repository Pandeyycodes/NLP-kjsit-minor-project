import { fireEvent, render, screen } from '@testing-library/react'
import userEvent, { type UserEvent } from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from 'vitest'
import App from './App'
import { API_BASE_URL, MAX_PDF_BYTES } from './api'
// A real response saved from the backend's POST /api/explain; /api/process-pdf
// returns the same shape plus a `pdf` field.
import explainResponse from './test/explain-response.json'
import type { ExplainResponse } from './types'

const PDF_RESPONSE: ExplainResponse = {
  ...(explainResponse as ExplainResponse),
  pdf: { page_count: 2, character_count: 135 },
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function pdfFile(name = 'notice.pdf', size?: number) {
  const file = new File(['%PDF-1.7 test'], name, { type: 'application/pdf' })
  if (size !== undefined) Object.defineProperty(file, 'size', { value: size })
  return file
}

async function choosePdfMode(user: UserEvent) {
  await user.click(screen.getByRole('button', { name: 'Upload PDF' }))
}

const fileInput = () => screen.getByLabelText('PDF document')

let fetchMock: Mock

beforeEach(() => {
  fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('PDF upload', () => {
  it('switches between pasted text and PDF upload', async () => {
    const user = userEvent.setup()
    render(<App />)

    expect(screen.getByRole('button', { name: 'Paste text' })).toHaveAttribute('aria-pressed', 'true')
    await user.type(screen.getByLabelText('Document text'), 'Keep me')

    await choosePdfMode(user)
    expect(screen.getByRole('button', { name: 'Upload PDF' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.queryByLabelText('Document text')).not.toBeInTheDocument()
    expect(screen.getByText(/Drag a PDF here/)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Paste text' }))
    expect(screen.getByLabelText('Document text')).toHaveValue('Keep me')
  })

  it('shows the selected file name and size, and can remove it', async () => {
    const user = userEvent.setup()
    render(<App />)
    await choosePdfMode(user)

    await user.upload(fileInput(), pdfFile('admission-notice.pdf', 250 * 1024))
    expect(screen.getByText('admission-notice.pdf')).toBeInTheDocument()
    expect(screen.getByText('250.0 KB')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Remove' }))
    expect(screen.queryByText('admission-notice.pdf')).not.toBeInTheDocument()
  })

  it('accepts a PDF dropped onto the drop area', async () => {
    const user = userEvent.setup()
    render(<App />)
    await choosePdfMode(user)

    fireEvent.drop(screen.getByTestId('dropzone'), { dataTransfer: { files: [pdfFile()] } })
    expect(screen.getByText('notice.pdf')).toBeInTheDocument()
  })

  it('rejects files that are not PDFs', async () => {
    const user = userEvent.setup({ applyAccept: false })
    render(<App />)
    await choosePdfMode(user)

    await user.upload(fileInput(), new File(['hello'], 'notes.txt', { type: 'text/plain' }))
    expect(screen.getByText('“notes.txt” is not a PDF. Please choose a .pdf file.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Remove' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Explain Document' }))
    expect(screen.getByText('Choose a PDF file first.')).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('rejects PDFs over 5 MB before uploading', async () => {
    const user = userEvent.setup()
    render(<App />)
    await choosePdfMode(user)

    await user.upload(fileInput(), pdfFile('big.pdf', MAX_PDF_BYTES + 1))
    expect(screen.getByText('“big.pdf” (5.0 MB) is larger than the 5 MB limit.')).toBeInTheDocument()
    await user.upload(fileInput(), pdfFile('bigger.pdf', 7.5 * 1024 * 1024))
    expect(screen.getByText('“bigger.pdf” (7.5 MB) is larger than the 5 MB limit.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Explain Document' }))
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('uploads the PDF with the selected language and shows the results', async () => {
    const user = userEvent.setup()
    fetchMock.mockResolvedValue(jsonResponse({ ...PDF_RESPONSE, language: 'hinglish' }))
    render(<App />)
    await choosePdfMode(user)

    await user.click(screen.getByRole('radio', { name: 'Hinglish' }))
    const file = pdfFile()
    await user.upload(fileInput(), file)
    await user.click(screen.getByRole('button', { name: 'Explain Document' }))

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe(`${API_BASE_URL}/api/process-pdf`)
    expect(options.method).toBe('POST')
    expect(options.body).toBeInstanceOf(FormData)
    expect(options.body.get('language')).toBe('hinglish')
    expect(options.body.get('file')).toBe(file)

    expect(await screen.findByText(/From notice\.pdf · 2 pages · Hinglish rules/)).toBeInTheDocument()
    for (const line of PDF_RESPONSE.explanation) {
      expect(screen.getByText(line)).toBeInTheDocument()
    }
    expect(screen.getByRole('heading', { name: 'Original (text read from the PDF)' })).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: 'Keep this document ready: resume' })).toBeInTheDocument()
  })

  it('shows a loading message while the PDF is processed', async () => {
    const user = userEvent.setup()
    fetchMock.mockReturnValue(new Promise(() => {}))
    render(<App />)
    await choosePdfMode(user)

    await user.upload(fileInput(), pdfFile())
    await user.click(screen.getByRole('button', { name: 'Explain Document' }))

    expect(screen.getByRole('status')).toHaveTextContent('Reading your PDF…')
    expect(screen.getByRole('button', { name: 'Explaining…' })).toBeDisabled()
  })

  it('shows the backend message for a PDF without readable text', async () => {
    const user = userEvent.setup()
    const message =
      'No readable text was found in this PDF. It may be a scanned or image-only ' +
      'document, which Samjho cannot read yet.'
    fetchMock.mockResolvedValue(jsonResponse({ detail: message }, 422))
    render(<App />)
    await choosePdfMode(user)

    await user.upload(fileInput(), pdfFile('scan.pdf'))
    await user.click(screen.getByRole('button', { name: 'Explain Document' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(message)
  })

  it('shows an error when the upload fails', async () => {
    const user = userEvent.setup()
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))
    render(<App />)
    await choosePdfMode(user)

    await user.upload(fileInput(), pdfFile())
    await user.click(screen.getByRole('button', { name: 'Explain Document' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Could not reach the Samjho server')
  })
})
