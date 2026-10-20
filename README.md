# Samjho

Samjho ("समझो", *understand*) helps students read official documents such as college
notices, job descriptions and government letters. Paste the text or upload a PDF, and
Samjho:

- rewrites common formal phrases in simpler words ("prior to" → "before", "से पूर्व" → "से पहले");
- finds **deadlines and dates, fees, eligibility conditions, required documents and action items**;
- writes a short explanation and a **checklist** built only from what it found;
- shows the sentence each finding came from, so you can check it against the original.

It is a **rule-based NLP** project developed as a KJSIT minor project. It uses hand-written
dictionaries and regular expressions, not AI models or external services, so the same input
always gives the same output.

## Architecture

```
frontend/  React + Vite + TypeScript (plain CSS)
   │  POST /api/explain (JSON)  or  POST /api/process-pdf (multipart)
   ▼
backend/   FastAPI (Python)
   app/main.py                    API endpoints, validation, CORS, upload size limit
   app/pdf_extraction.py          PDF → text in memory (PyMuPDF)
   app/nlp/text_processing.py     whitespace normalisation, sentence splitting, tokens
   app/nlp/simplification.py      phrase rules from phrase_rules_{en,hi,hinglish}.json
   app/nlp/information_extraction.py  dates, deadlines, fees, eligibility, documents, actions
   app/nlp/negation.py            stops rules from reversing negated sentences
   app/nlp/document_explainer.py  combines the above into explanation + checklist
```

**Technology:** Python 3, FastAPI, Uvicorn, PyMuPDF, python-multipart, pytest; React 19,
Vite, TypeScript, Vitest and Testing Library. No database, no AI APIs.

## Setup on Windows

Requirements: Python 3.11+ (needed by PyMuPDF) and Node.js 22.12+ (needed by Vitest).

### Backend (PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

If activation is blocked, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and
activate again. The API runs at http://127.0.0.1:8000 and interactive docs are at
http://127.0.0.1:8000/docs.

### Frontend (a second PowerShell window; keep the backend running)

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The frontend calls `http://127.0.0.1:8000` by default. To use a
different backend, copy `frontend/.env.example` to `frontend/.env.local` and change
`VITE_API_BASE_URL`.

## Running the tests and build

```powershell
# backend (with the virtual environment active)
cd backend
python -m pytest -q

# frontend
cd frontend
npm test
npm run build      # type-checks and builds into frontend/dist
npm run lint
```

## API endpoints

| Method and path | Input | Returns |
|---|---|---|
| `GET /` | – | project name and status |
| `GET /health` | – | `{"status": "healthy"}` |
| `POST /api/process-text` | `{"text"}` | normalised text, sentences, tokens |
| `POST /api/simplify` | `{"text", "language"}` | simplified text and each phrase replaced |
| `POST /api/extract-info` | `{"text", "language"}` | deadlines, dates, fees, eligibility, documents, action items |
| `POST /api/explain` | `{"text", "language"}` | all of the above plus explanation, checklist and per-sentence status |
| `POST /api/process-pdf` | form fields `file` (PDF) and `language` | same as `/api/explain` plus `pdf.page_count` |

`language` is `en`, `hi` or `hinglish` (default `en`). Text is limited to 20,000 characters
and PDFs to 5 MB. Invalid input returns HTTP 422 (413 for files over 5 MB, 415 for non-PDF
files) with a readable message.

Example:

```json
POST /api/explain
{"text": "Students with at least 60% marks must submit their resume by 15 November 2026. The application fee is ₹500.", "language": "en"}
```

returns, among other fields, the explanation `"Deadline mentioned: 15 November 2026."`,
`"Amounts mentioned: ₹500."`, and checklist steps such as
`"Keep this document ready: resume"`.

## Supported languages

| Language | Script | What is covered |
|---|---|---|
| English (`en`) | Latin | 20 phrase rules, English month names, deadline words such as "deadline", "last date", "by" |
| Hindi (`hi`) | Devanagari | 20 phrase rules, Hindi month names, Devanagari digits, words such as "अंतिम तिथि", "तक" |
| Hinglish (`hinglish`) | Hindi in Latin letters | 20 phrase rules, words such as "antim tithi", "tak", "upload karein" |

The user chooses the language; rules from one language are never applied to another.

## Limits of rule-based processing

Samjho only recognises the phrases and patterns written into its rules. Please keep these
limits in mind and always confirm important details in the original document.

- **No translation.** Samjho does not translate between languages. Only listed phrases are
  simplified; everything else is left exactly as written, and sentences no rule covers are
  marked `unsupported`.
- **Small dictionaries.** About 20 phrase rules per language. Hinglish spellings vary
  ("purv" / "poorv"), and only the spellings in the dictionary match.
- **Negation.** A phrase or action right after a negation word ("not", "no", "न", "मत", "mat")
  is left alone, so "Do not bring phones" is not turned into a "bring" action. Negation
  further away in a sentence may be missed.
- **Deadlines.** A date counts as a deadline only with nearby wording such as "deadline",
  "last date", "by", "before", "until", "तक" or "tak". Some non-deadline sentences still
  match, e.g. "born before 1 January 2000" or "was open till 15 August 1947". A deadline word
  placed *after* its date ("15 नवंबर अंतिम तिथि है") is not detected.
- **Dates.** A date such as `05/11/2026` (5 November or May 11) is reported as ambiguous, and
  a date without a year is reported as "year not stated"; Samjho never guesses. Two-digit
  years are not recognised.
- **Amounts.** Rupee amounts need ₹, Rs, INR or "rupees"/"रुपये". Lakh, crore, thousand and
  LPA are understood; other units are not.
- **Eligibility.** Samjho shows the eligibility sentences it finds but never decides whether
  the reader is eligible.

## PDF limitations

- Only **text-based PDFs** are supported. Scanned or photographed documents contain images,
  not text, and Samjho has **no OCR**; such files return "No readable text was found".
- Password-protected, damaged or empty PDFs are rejected with a message.
- Files over 5 MB or with more than 20,000 characters of text are rejected.
- Text order follows the PDF's internal layout, so multi-column pages and tables may be read
  in an unexpected order.
- Uploaded files are processed in memory and never saved by Samjho. (While a request is
  being handled, the web framework may briefly buffer a large upload in a temporary file,
  which it deletes when the request ends.)

## Configuration for deployment

- `CORS_ORIGINS` (backend): comma-separated list of allowed frontend origins, for example
  `https://samjho.example.com`. The default allows only the local Vite servers on ports
  5173 and 4173.
- `VITE_API_BASE_URL` (frontend, at build time): the public URL of the backend.
