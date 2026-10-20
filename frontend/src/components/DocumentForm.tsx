import type { FormEvent } from 'react'
import { MAX_TEXT_LENGTH } from '../api'
import type { Language } from '../types'
import PdfPicker from './PdfPicker'

export type InputMode = 'text' | 'pdf'

const LANGUAGE_OPTIONS: { value: Language; label: string; native?: string }[] = [
  { value: 'en', label: 'English' },
  { value: 'hi', label: 'Hindi', native: 'हिन्दी' },
  { value: 'hinglish', label: 'Hinglish' },
]

const MODE_OPTIONS: { value: InputMode; label: string }[] = [
  { value: 'text', label: 'Paste text' },
  { value: 'pdf', label: 'Upload PDF' },
]

interface Props {
  mode: InputMode
  text: string
  file: File | null
  language: Language
  loading: boolean
  error: string
  onModeChange: (mode: InputMode) => void
  onTextChange: (text: string) => void
  onFileSelect: (file: File | null) => void
  onLanguageChange: (language: Language) => void
  onSubmit: () => void
}

export default function DocumentForm({
  mode,
  text,
  file,
  language,
  loading,
  error,
  onModeChange,
  onTextChange,
  onFileSelect,
  onLanguageChange,
  onSubmit,
}: Props) {
  const tooLong = text.length > MAX_TEXT_LENGTH

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    onSubmit()
  }

  return (
    <form className="card input-card" onSubmit={handleSubmit} noValidate>
      <div className="mode-switch" role="group" aria-label="Input method">
        {MODE_OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            className="mode-button"
            aria-pressed={mode === option.value}
            onClick={() => onModeChange(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>

      {mode === 'text' ? (
        <div className="field">
          <label htmlFor="document-text" className="field-label">
            Document text
          </label>
          <textarea
            id="document-text"
            value={text}
            onChange={(event) => onTextChange(event.target.value)}
            placeholder="Paste a college notice, job description or official letter here…"
            rows={10}
            lang={language === 'en' ? 'en' : 'hi'}
            aria-invalid={Boolean(error) || tooLong}
            aria-describedby="text-help"
          />
          <div id="text-help" className="field-help">
            {error ? (
              <span className="field-error">{error}</span>
            ) : (
              <span>Plain text only. Nothing is stored.</span>
            )}
            <span className={tooLong ? 'counter counter-over' : 'counter'}>
              {text.length.toLocaleString('en-IN')} / {MAX_TEXT_LENGTH.toLocaleString('en-IN')}
            </span>
          </div>
        </div>
      ) : (
        <PdfPicker file={file} error={error} onSelect={onFileSelect} />
      )}

      <div className="form-footer">
        <fieldset className="language-picker">
          <legend className="field-label">Document language</legend>
          <div className="segments">
            {LANGUAGE_OPTIONS.map((option) => (
              <label key={option.value} className="segment">
                <input
                  type="radio"
                  name="language"
                  value={option.value}
                  checked={language === option.value}
                  onChange={() => onLanguageChange(option.value)}
                />
                <span>
                  {option.label}
                  {option.native && (
                    <span className="segment-native" lang="hi">
                      {' '}
                      {option.native}
                    </span>
                  )}
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <button type="submit" className="button button-primary" disabled={loading}>
          {loading && <span className="spinner" aria-hidden="true" />}
          {loading ? 'Explaining…' : 'Explain Document'}
        </button>
      </div>
    </form>
  )
}
