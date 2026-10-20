import { useState } from 'react'
import type { ChecklistItem, FactCategory } from '../types'
import CopyButton from './CopyButton'

const CATEGORY_LABELS: Record<FactCategory, string> = {
  eligibility: 'Eligibility',
  required_documents: 'Document',
  action_items: 'Action',
  fees: 'Fee',
  deadlines: 'Deadline',
  dates: 'Date',
}

interface Props {
  items: ChecklistItem[]
  lang: string
}

export default function Checklist({ items, lang }: Props) {
  // Ticks live only in this component's state: they reset on reload or a new explanation.
  const [done, setDone] = useState<Set<number>>(() => new Set())

  function toggle(index: number) {
    setDone((previous) => {
      const next = new Set(previous)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }

  const copyText = () =>
    items.map((item, index) => `${done.has(index) ? '[x]' : '[ ]'} ${item.task}`).join('\n')

  return (
    <article className="card">
      <div className="card-header">
        <div>
          <h3>Suggested checklist</h3>
          <p className="card-subtitle">Built only from details found in the document.</p>
        </div>
        {items.length > 0 && <CopyButton label="Copy checklist" getText={copyText} />}
      </div>

      {items.length === 0 ? (
        <p className="muted">
          No steps could be suggested because no supported details were found.
        </p>
      ) : (
        <>
          <p className="progress" aria-live="polite">
            {done.size} of {items.length} done
          </p>
          <ul className="checklist" lang={lang}>
            {items.map((item, index) => (
              <li key={index} className={done.has(index) ? 'is-done' : undefined}>
                <label>
                  <input
                    type="checkbox"
                    checked={done.has(index)}
                    onChange={() => toggle(index)}
                  />
                  <span>{item.task}</span>
                </label>
                <div className="tags">
                  <span className="tag">{CATEGORY_LABELS[item.category]}</span>
                  {item.needs_verification && <span className="tag tag-warn">Verify date</span>}
                </div>
              </li>
            ))}
          </ul>
          <p className="fine-print">Ticks are kept only while this page is open. They are not saved.</p>
        </>
      )}
    </article>
  )
}
