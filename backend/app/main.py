from fastapi import FastAPI
from pydantic import BaseModel, Field, field_validator

from app.nlp.text_processing import normalize_text, split_sentences, tokenize_text

MAX_TEXT_LENGTH = 20_000

app = FastAPI(title="Samjho")


class TextInput(BaseModel):
    text: str = Field(max_length=MAX_TEXT_LENGTH)

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be empty")
        return value


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
