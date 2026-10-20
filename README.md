# Samjho

Samjho is a rule-based NLP document simplification and information extraction project, developed as a KJSIT minor project.

## Current milestone

- `backend/`: FastAPI app with rule-based text processing, phrase simplification (English, Hindi, Hinglish), information extraction, `POST /api/explain` for pasted text and `POST /api/process-pdf` for text-based PDF uploads (up to 5 MB, read in memory with PyMuPDF; scanned PDFs are not supported).
- `frontend/`: React + Vite + TypeScript website that accepts pasted text or a PDF and shows the explanation, extracted details and a checklist.

## Backend setup (Windows PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If activation is blocked, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then activate again.

## Run tests

```powershell
python -m pytest -q
```

## Start the server

```powershell
python -m uvicorn app.main:app --reload
```

- API root: http://127.0.0.1:8000/
- Health check: http://127.0.0.1:8000/health
- API docs: http://127.0.0.1:8000/docs

## Frontend (Windows PowerShell, in a second terminal)

Requires Node.js. Keep the backend running.

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The backend URL defaults to `http://127.0.0.1:8000`; to change it, copy `frontend/.env.example` to `frontend/.env.local` and edit `VITE_API_BASE_URL`.

```powershell
npm test          # frontend tests
npm run build     # production build into frontend/dist
```
