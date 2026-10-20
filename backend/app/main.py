import os
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.nlp.document_explainer import explain_document
from app.nlp.information_extraction import extract_information
from app.nlp.simplification import simplify_text
from app.nlp.text_processing import normalize_text, split_sentences, tokenize_text
from app.pdf_extraction import MAX_PDF_BYTES, PDF_LIMIT_TEXT, PdfError, extract_pdf_text

MAX_TEXT_LENGTH = 20_000
Language = Literal["en", "hi", "hinglish"]

# Local Vite dev (5173) and preview (4173) servers. Override with a
# comma-separated CORS_ORIGINS environment variable.
DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173"
)


def parse_origins(value: str) -> list[str]:
    """Split a comma-separated origin list, ignoring spaces and empty entries."""
    return [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]


CORS_ORIGINS = parse_origins(os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS))
# The largest allowed PDF plus room for the multipart form headers.
MAX_UPLOAD_REQUEST_BYTES = MAX_PDF_BYTES + 64 * 1024

app = FastAPI(title="Samjho")


# Registered before CORS so the CORS middleware wraps it and its 413 reply
# still carries CORS headers the browser can read.
@app.middleware("http")
async def reject_large_uploads(request: Request, call_next):
    """Refuse an oversized upload from its Content-Length, before reading the body."""
    if request.url.path == "/api/process-pdf":
        length = request.headers.get("content-length", "")
        if length.isdigit() and int(length) > MAX_UPLOAD_REQUEST_BYTES:
            return JSONResponse(
                {"detail": f"The PDF is larger than the {PDF_LIMIT_TEXT} limit."}, status_code=413
            )
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class TextInput(BaseModel):
    text: str = Field(max_length=MAX_TEXT_LENGTH)

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be empty")
        return value


class LanguageTextInput(TextInput):
    language: Language = "en"


@app.get("/")
def root():
    return {"project": "Samjho", "message": "Samjho backend is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/api/process-text")
def process_text(payload: TextInput):
    normalized = normalize_text(payload.text)
    sentences = split_sentences(normalized)
    tokens = tokenize_text(normalized)
    return {
        "normalized_text": normalized,
        "sentences": sentences,
        "sentence_count": len(sentences),
        "tokens": tokens,
        "token_count": len(tokens),
    }


@app.post("/api/simplify")
def simplify(payload: LanguageTextInput):
    return simplify_text(payload.text, payload.language)


@app.post("/api/extract-info")
def extract_info(payload: LanguageTextInput):
    return extract_information(payload.text, payload.language)


@app.post("/api/explain")
def explain(payload: LanguageTextInput):
    return explain_document(payload.text, payload.language)


@app.post("/api/process-pdf")
def process_pdf(file: UploadFile = File(...), language: Language = Form("en")):
    try:
        # Read at most one byte past the limit; the upload is never written to our storage.
        data = file.file.read(MAX_PDF_BYTES + 1)
    finally:
        file.file.close()
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(413, f"The PDF is larger than the {PDF_LIMIT_TEXT} limit.")

    try:
        text, page_count = extract_pdf_text(data)
    except PdfError as error:
        raise HTTPException(error.status_code, str(error))
    if not text.strip():
        raise HTTPException(
            422,
            "No readable text was found in this PDF. It may be a scanned or image-only "
            "document, which Samjho cannot read yet.",
        )

    # Same text and language validation as POST /api/explain.
    try:
        payload = LanguageTextInput(text=text, language=language)
    except ValidationError:
        raise HTTPException(
            422,
            f"This PDF contains {len(text):,} characters of text. "
            f"The limit is {MAX_TEXT_LENGTH:,}.",
        )
    result = explain_document(payload.text, payload.language)
    return {**result, "pdf": {"page_count": page_count, "character_count": len(text)}}
