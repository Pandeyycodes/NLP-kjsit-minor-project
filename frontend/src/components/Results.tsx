import type { ReactNode } from 'react'
import type { DateFinding, ExplainResponse, Finding, Language } from '../types'
import Checklist from './Checklist'
import CopyButton from './CopyButton'

const LANGUAGE_NAMES: Record<Language, string> = { en: 'English', hi: 'Hindi', hinglish: 'Hinglish' }
const LANG_ATTRIBUTES: Record<Language, string> = { en: 'en', hi: 'hi', hinglish: 'hi-Latn' }

interface FactItem {
  value: ReactNode
  details?: ReactNode
  source: string
}

function FactCard({ title, items, lang }: { title: string; items: FactItem[]; lang: string }) {
  return (
    <article className="card fact-card">
      <h4>
        {title} <span className="count">{items.length}</span>
      </h4>
      {items.length === 0 ? (
        <p className="muted">Not found in this document.</p>
      ) : (
        <ul className="fact-list" lang={lang}>
          {items.map((item, index) => (
            <li key={index}>
              <div className="fact-value">{item.value}</div>
              {item.details && <div className="fact-details">{item.details}</div>}
              <blockquote className="fact-source">“{item.source}”</blockquote>
            </li>
          ))}
        </ul>
      )}
    </article>
  )
}

function dateItem(finding: DateFinding, cue?: string): FactItem {
  return {
    value: finding.value,
    details: (
      <>
        {finding.iso && <span className="tag">{finding.iso}</span>}
        {finding.note && <span className="tag tag-warn">Check: {finding.note}</span>}
        {cue && <span className="tag tag-plain">matched “{cue}”</span>}
      </>
    ),
    source: finding.source,
  }
}

const plainItem = (finding: Finding): FactItem => ({ value: finding.value, source: finding.source })

interface Props {
  result: ExplainResponse
  /** Set when the result came from an uploaded PDF. */
  fileName?: string | null
}

export default function Results({ result, fileName }: Props) {
  const { facts } = result
  const lang = LANG_ATTRIBUTES[result.language]
  const deadlineKeys = new Set(facts.deadlines.map((d) => `${d.value}|${d.source}`))
  const otherDates = facts.dates.filter((d) => !deadlineKeys.has(`${d.value}|${d.source}`))
  const unsupported = result.sentences.filter((s) => s.status === 'unsupported').length

  return (
    <div className="results">
      <div className="results-header">
        <h2>Results</h2>
        <p className="meta">
          {result.pdf && fileName && (
            <>
              From {fileName} · {result.pdf.page_count} page{result.pdf.page_count === 1 ? '' : 's'}{' '}
              ·{' '}
            </>
          )}
          {LANGUAGE_NAMES[result.language]} rules · {result.sentences.length} sentence
          {result.sentences.length === 1 ? '' : 's'}
          {unsupported > 0 && ` · ${unsupported} not covered by the rules`}
        </p>
      </div>

      <div className="results-top">
        <article className="card">
          <div className="card-header">
            <div>
              <h3>What this document says</h3>
              <p className="card-subtitle">A short summary of what Samjho recognised.</p>
            </div>
            <CopyButton label="Copy explanation" getText={() => result.explanation.join('\n')} />
          </div>
          <ul className="explanation" lang={lang}>
            {result.explanation.map((line, index) => (
              <li key={index}>{line}</li>
            ))}
          </ul>
        </article>

        <Checklist items={result.checklist} lang={lang} />
      </div>

      <section className="results-section">
        <div className="section-heading">
          <h3>Found in the document</h3>
          <p className="card-subtitle">Each detail shows the sentence it came from, so you can check it.</p>
        </div>
        <div className="facts-grid">
          <FactCard
            title="Deadlines"
            items={facts.deadlines.map((d) => dateItem(d, d.cue))}
            lang={lang}
          />
          <FactCard title="Other dates" items={otherDates.map((d) => dateItem(d))} lang={lang} />
          <FactCard title="Fees and amounts" items={facts.fees.map(plainItem)} lang={lang} />
          <FactCard title="Eligibility" items={facts.eligibility.map(plainItem)} lang={lang} />
          <FactCard
            title="Required documents"
            items={facts.required_documents.map(plainItem)}
            lang={lang}
          />
          <FactCard title="Action items" items={facts.action_items.map(plainItem)} lang={lang} />
        </div>
      </section>

      <section className="results-section">
        <div className="section-heading">
          <h3>Original and simplified text</h3>
          <p className="card-subtitle">
            {result.transformations.length === 0
              ? 'No phrases needed simplifying.'
              : `${result.transformations.length} phrase${
                  result.transformations.length === 1 ? ' was' : 's were'
                } replaced with simpler wording.`}
          </p>
        </div>
        {result.transformations.length > 0 && (
          <ul className="changes" lang={lang}>
            {result.transformations.map((change, index) => (
              <li key={index}>
                <del>{change.original}</del> → <ins>{change.replacement}</ins>
              </li>
            ))}
          </ul>
        )}
        <div className="compare">
          <article className="card">
            <h4>{result.pdf ? 'Original (text read from the PDF)' : 'Original'}</h4>
            <p className="document-text" lang={lang}>
              {result.original_text}
            </p>
          </article>
          <article className="card">
            <h4>Simplified</h4>
            <p className="document-text" lang={lang}>
              {result.simplified_text}
            </p>
          </article>
        </div>
      </section>
    </div>
  )
}
