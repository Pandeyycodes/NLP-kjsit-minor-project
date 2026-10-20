import { fireEvent, render, screen } from '@testing-library/react'
import userEvent, { type UserEvent } from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from 'vitest'
import App from './App'
import { API_BASE_URL } from './api'
// A real response saved from the backend's POST /api/explain.
import explainResponse from './test/explain-response.json'
import type { ExplainResponse } from './types'

const RESPONSE = explainResponse as ExplainResponse
const SAMPLE = RESPONSE.original_text

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function factCard(title: RegExp) {
  return screen.getByRole('heading', { name: title }).closest('article') as HTMLElement
}

async function explain(user: UserEvent, text = SAMPLE) {
  await user.click(screen.getByLabelText('Document text'))
  await user.paste(text)
  await user.click(screen.getByRole('button', { name: 'Explain Document' }))
}

let fetchMock: Mock

beforeEach(() => {
  fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('form', () => {
  it('shows the empty state with English selected by default', () => {
    render(<App />)
    expect(screen.getByText('Your explanation will appear here')).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: 'English' })).toBeChecked()
    expect(screen.getByRole('radio', { name: /Hindi/ })).not.toBeChecked()
    expect(screen.getByRole('radio', { name: 'Hinglish' })).not.toBeChecked()
  })

  it('sends the text and selected language to /api/explain', async () => {
    const user = userEvent.setup()
    fetchMock.mockResolvedValue(jsonResponse({ ...RESPONSE, language: 'hi' }))
    render(<App />)

    await user.click(screen.getByRole('radio', { name: /Hindi/ }))
    expect(screen.getByRole('radio', { name: /Hindi/ })).toBeChecked()
    await explain(user, 'अंतिम तिथि 15 नवंबर 2026 है।')

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe(`${API_BASE_URL}/api/explain`)
    expect(options.method).toBe('POST')
    expect(JSON.parse(options.body)).toEqual({
      text: 'अंतिम तिथि 15 नवंबर 2026 है।',
      language: 'hi',
    })
  })

  it('does not call the backend for empty or whitespace-only input', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: 'Explain Document' }))
    expect(screen.getByText('Paste some document text first.')).toBeInTheDocument()

    await explain(user, '   ')
    expect(screen.getByText('Paste some document text first.')).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('does not call the backend for text over the limit', async () => {
    const user = userEvent.setup()
    render(<App />)

    fireEvent.change(screen.getByLabelText('Document text'), { target: { value: 'a'.repeat(20_001) } })
    await user.click(screen.getByRole('button', { name: 'Explain Document' }))

    expect(screen.getByText(/The limit is 20,000/)).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('shows a loading indicator while the backend is working', async () => {
    const user = userEvent.setup()
    fetchMock.mockReturnValue(new Promise(() => {}))
    render(<App />)

    await explain(user)

    expect(screen.getByRole('button', { name: 'Explaining…' })).toBeDisabled()
    expect(screen.getByRole('status')).toHaveTextContent('Reading your document…')
  })
})

describe('results', () => {
  it('renders every section from the backend response', async () => {
    const user = userEvent.setup()
    fetchMock.mockResolvedValue(jsonResponse(RESPONSE))
    render(<App />)

    await explain(user)

    expect(await screen.findByRole('heading', { name: 'Results' })).toBeInTheDocument()
    for (const line of RESPONSE.explanation) {
      expect(screen.getByText(line)).toBeInTheDocument()
    }
    expect(screen.getByText(/3 sentences · 1 not covered by the rules/)).toBeInTheDocument()

    const deadlines = factCard(/^Deadlines/)
    expect(deadlines).toHaveTextContent('15 November 2026')
    expect(deadlines).toHaveTextContent('2026-11-15')
    expect(deadlines).toHaveTextContent('matched “by”')
    expect(factCard(/^Other dates/)).toHaveTextContent('Not found in this document.')
    expect(factCard(/^Fees and amounts/)).toHaveTextContent('₹500')
    expect(factCard(/^Fees and amounts/)).toHaveTextContent('“The application fee is ₹500.”')
    expect(factCard(/^Eligibility/)).toHaveTextContent('at least 60% marks')
    expect(factCard(/^Required documents/)).toHaveTextContent('resume')
    expect(factCard(/^Action items/)).toHaveTextContent('submit')

    expect(factCard(/^Original$/)).toHaveTextContent(RESPONSE.original_text)
    expect(factCard(/^Simplified$/)).toHaveTextContent(RESPONSE.simplified_text)
    expect(screen.getByText('No phrases needed simplifying.')).toBeInTheDocument()

    for (const item of RESPONSE.checklist) {
      expect(screen.getByRole('checkbox', { name: item.task })).not.toBeChecked()
    }
  })

  it('moves focus to the results so keyboard users land on them', async () => {
    const user = userEvent.setup()
    fetchMock.mockResolvedValue(jsonResponse(RESPONSE))
    render(<App />)

    await explain(user)

    expect(await screen.findByRole('heading', { name: 'Results' })).toHaveFocus()
  })

  it('shows phrase changes and date warnings returned by the backend', async () => {
    const user = userEvent.setup()
    fetchMock.mockResolvedValue(
      jsonResponse({
        ...RESPONSE,
        simplified_text: 'Submit before 05/11/2026.',
        transformations: [{ original: 'prior to', replacement: 'before', start: 7 }],
        facts: {
          ...RESPONSE.facts,
          deadlines: [
            {
              value: '05/11/2026',
              iso: null,
              note: 'ambiguous day/month order',
              rule: 'deadline_cue',
              cue: 'by',
              source: 'Submit by 05/11/2026.',
            },
          ],
        },
        checklist: [
          {
            category: 'deadlines',
            task: 'Note the deadline: 05/11/2026 (ambiguous day/month order)',
            value: '05/11/2026',
            source: 'Submit by 05/11/2026.',
            needs_verification: true,
          },
        ],
      }),
    )
    render(<App />)

    await explain(user)

    expect(await screen.findByText('1 phrase was replaced with simpler wording.')).toBeInTheDocument()
    expect(screen.getByText('prior to')).toBeInTheDocument()
    expect(factCard(/^Deadlines/)).toHaveTextContent('Check: ambiguous day/month order')
    expect(screen.getByText('Verify date')).toBeInTheDocument()
  })
})

describe('errors', () => {
  it('explains when the backend cannot be reached', async () => {
    const user = userEvent.setup()
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))
    render(<App />)

    await explain(user)

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Could not reach the Samjho server')
    expect(alert).toHaveTextContent(API_BASE_URL)
  })

  it('shows validation messages from the backend', async () => {
    const user = userEvent.setup()
    fetchMock.mockResolvedValue(
      jsonResponse(
        { detail: [{ loc: ['body', 'text'], msg: 'Value error, text must not be empty' }] },
        422,
      ),
    )
    render(<App />)

    await explain(user)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The server could not accept this input: text must not be empty.',
    )
  })

  it('shows a general message for server errors', async () => {
    const user = userEvent.setup()
    fetchMock.mockResolvedValue(new Response('Internal Server Error', { status: 500 }))
    render(<App />)

    await explain(user)

    expect(await screen.findByRole('alert')).toHaveTextContent('HTTP 500')
  })
})

describe('checklist and copying', () => {
  it('ticks and unticks checklist items locally', async () => {
    const user = userEvent.setup()
    fetchMock.mockResolvedValue(jsonResponse(RESPONSE))
    render(<App />)
    await explain(user)

    const total = RESPONSE.checklist.length
    expect(await screen.findByText(`0 of ${total} done`)).toBeInTheDocument()
    const item = screen.getByRole('checkbox', { name: 'Keep this document ready: resume' })

    await user.click(item)
    expect(item).toBeChecked()
    expect(screen.getByText(`1 of ${total} done`)).toBeInTheDocument()

    await user.click(item)
    expect(item).not.toBeChecked()
    expect(screen.getByText(`0 of ${total} done`)).toBeInTheDocument()
    expect(screen.getByText(/They are not saved/)).toBeInTheDocument()
  })

  it('copies the explanation and the checklist', async () => {
    const user = userEvent.setup()
    fetchMock.mockResolvedValue(jsonResponse(RESPONSE))
    render(<App />)
    await explain(user)

    await user.click(await screen.findByRole('button', { name: 'Copy explanation' }))
    expect(await navigator.clipboard.readText()).toBe(RESPONSE.explanation.join('\n'))
    expect(screen.getByRole('button', { name: 'Copied' })).toBeInTheDocument()

    await user.click(screen.getByRole('checkbox', { name: 'Keep this document ready: resume' }))
    await user.click(screen.getByRole('button', { name: 'Copy checklist' }))
    const copied = await navigator.clipboard.readText()
    expect(copied).toContain('[x] Keep this document ready: resume')
    expect(copied).toContain('[ ] Check this amount: ₹500')
  })
})
