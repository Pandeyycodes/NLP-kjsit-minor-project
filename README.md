# Samjho

Samjho is a rule-based NLP document simplification and information extraction project, developed as a KJSIT minor project.

## Current milestone

Step 1 provides only the backend foundation: a minimal FastAPI app with a root endpoint and a health check, plus tests. Text processing, extraction, and the frontend come in later steps.

## Setup (Windows PowerShell)

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
