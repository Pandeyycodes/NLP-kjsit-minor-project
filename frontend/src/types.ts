// Mirrors the JSON returned by POST /api/explain (backend/app/nlp/document_explainer.py)
// and POST /api/process-pdf, which adds the `pdf` field.

export type Language = 'en' | 'hi' | 'hinglish'

export interface Finding {
  value: string
  rule: string
  source: string
}

export interface DateFinding extends Finding {
  iso: string | null
  note: string | null
}

export interface DeadlineFinding extends DateFinding {
  cue: string
}

export interface FeeFinding extends Finding {
  amount: number
  currency: string
}

export interface Facts {
  deadlines: DeadlineFinding[]
  dates: DateFinding[]
  fees: FeeFinding[]
  eligibility: Finding[]
  required_documents: Finding[]
  action_items: Finding[]
}

export type FactCategory = keyof Facts

export interface Transformation {
  original: string
  replacement: string
  start: number
}

export interface ChecklistItem {
  category: FactCategory
  task: string
  value: string
  source: string
  needs_verification: boolean
}

export interface SentenceInfo {
  original: string
  simplified: string
  categories: FactCategory[]
  status: 'explained' | 'simplified_only' | 'unsupported'
}

export interface ExplainResponse {
  language: Language
  original_text: string
  simplified_text: string
  transformations: Transformation[]
  explanation: string[]
  facts: Facts
  checklist: ChecklistItem[]
  sentences: SentenceInfo[]
  pdf?: PdfInfo
}

export interface PdfInfo {
  page_count: number
  character_count: number
}
