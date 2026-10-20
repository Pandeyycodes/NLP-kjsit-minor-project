import { useState } from 'react'
import { ApiError, MAX_TEXT_LENGTH, explainDocument, explainPdf } from './api'
import DocumentForm, { type InputMode } from './components/DocumentForm'
import Results from './components/Results'
import { checkPdfFile } from './files'
import type { ExplainResponse, Language } from './types'

type Status = 'idle' | 'loading' | 'success' | 'error'

export default function App() {
  const [mode, setMode] = useState<InputMode>('text')
  const [text, setText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  // Name of the PDF the current result came from, if any.
  const [resultFileName, setResultFileName] = useState<string | null>(null)
  const [language, setLanguage] = useState<Language>('en')
  const [status, setStatus] = useState<Status>('idle')
  const [result, setResult] = useState<ExplainResponse | null>(null)
  const [error, setError] = useState('')
  const [formError, setFormError] = useState('')
  // Changes on every successful run so the checklist starts fresh.
  const [runId, setRunId] = useState(0)

  function handleModeChange(value: InputMode) {
    setMode(value)
    setFormError('')
  }

  function handleTextChange(value: string) {
    setText(value)
    setFormError('')
  }

  function handleFileSelect(selected: File | null) {
    const problem = selected ? checkPdfFile(selected) : null
    setFile(problem ? null : selected)
    setFormError(problem ?? '')
  }

  /** Returns an error message, or null if the current input can be sent. */
  function validate(): string | null {
    if (mode === 'pdf') {
      return file ? checkPdfFile(file) : 'Choose a PDF file first.'
    }
    if (!text.trim()) return 'Paste some document text first.'
    if (text.length > MAX_TEXT_LENGTH) {
      return (
        `The text is ${text.length.toLocaleString('en-IN')} characters long. ` +
        `The limit is ${MAX_TEXT_LENGTH.toLocaleString('en-IN')}.`
      )
    }
    return null
  }

  async function handleSubmit() {
    const problem = validate()
    if (problem) {
      setFormError(problem)
      return
    }
    setFormError('')
    setStatus('loading')
    try {
      const pdf = mode === 'pdf' ? file : null
      setResult(pdf ? await explainPdf(pdf, language) : await explainDocument(text, language))
      setResultFileName(pdf ? pdf.name : null)
      setRunId((id) => id + 1)
      setStatus('success')
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : 'Something unexpected went wrong. Please try again.',
      )
      setStatus('error')
    }
  }

  return (
    <div className="page">
      <header className="site-header">
        <div className="container">
          <div className="brand">
            <span className="wordmark">Samjho</span>
            <span className="wordmark-native" lang="hi">
              समझो
            </span>
          </div>
          <p className="tagline">
            Paste a college notice, job post or official letter. Samjho simplifies the wording and
            pulls out deadlines, fees, eligibility, documents and next steps.
          </p>
        </div>
      </header>

      <main className="container main">
        <DocumentForm
          mode={mode}
          text={text}
          file={file}
          language={language}
          loading={status === 'loading'}
          error={formError}
          onModeChange={handleModeChange}
          onTextChange={handleTextChange}
          onFileSelect={handleFileSelect}
          onLanguageChange={setLanguage}
          onSubmit={handleSubmit}
        />

        {status === 'idle' && (
          <section className="card state-card empty-state">
            <h2>Your explanation will appear here</h2>
            <ol>
              <li>Paste the text of a notice, job description or letter, or upload it as a PDF.</li>
              <li>Choose the language it is written in.</li>
              <li>
                Press <strong>Explain Document</strong> to see deadlines, fees, documents and a
                checklist.
              </li>
            </ol>
          </section>
        )}

        {status === 'loading' && (
          <section className="card state-card loading-state" role="status">
            <span className="spinner spinner-large" aria-hidden="true" />
            <p>{mode === 'pdf' ? 'Reading your PDF…' : 'Reading your document…'}</p>
          </section>
        )}

        {status === 'error' && (
          <section className="card state-card error-state" role="alert">
            <h2>Could not explain this document</h2>
            <p>{error}</p>
          </section>
        )}

        {status === 'success' && result && (
          <Results key={runId} result={result} fileName={resultFileName} />
        )}
      </main>

      <footer className="site-footer">
        <div className="container">
          <p>
            Samjho uses fixed language rules, not AI. Always confirm important details in the
            original document.
          </p>
          <p>KJSIT minor project</p>
        </div>
      </footer>
    </div>
  )
}
