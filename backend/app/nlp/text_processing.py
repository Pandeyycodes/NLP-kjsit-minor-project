"""Deterministic text processing helpers (standard library only)."""

import re

# Python's \w misses Devanagari vowel signs and virama, so include the block
# explicitly (minus the danda punctuation marks U+0964/U+0965), plus ZWNJ/ZWJ.
WORD_CHAR = r"[\wऀ-ॣ०-ॿ‌‍]"
_WORD = WORD_CHAR + "+"
# Words may be joined by apostrophes or hyphens; digits by . or , (3.5, 1,000).
_TOKEN_RE = re.compile(rf"{_WORD}(?:(?:['’\-]|(?<=\d)[.,](?=\d)){_WORD})*|\S")

# Sentence-ending punctuation (with any closing quotes/brackets) followed by whitespace.
_BOUNDARY_RE = re.compile(r"([.!?]+[\"'”’)\]]*|[।॥]+)\s+")

_ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc", "no", "nos",
    "govt", "dept", "approx", "fig", "sec", "art", "rs", "ltd", "inc", "co",
}


def normalize_text(text: str) -> str:
    """Collapse repeated whitespace within lines and blank-line runs between paragraphs."""
    paragraphs, current = [], []
    for line in text.splitlines():
        line = " ".join(line.split())
        if line:
            current.append(line)
        elif current:
            paragraphs.append("\n".join(current))
            current = []
    if current:
        paragraphs.append("\n".join(current))
    return "\n\n".join(paragraphs)


def _is_boundary(paragraph: str, match: re.Match) -> bool:
    punct = match.group(1)
    if punct[0] in "।॥":
        return True
    # A lowercase continuation means the period was not a sentence end.
    if paragraph[match.end():match.end() + 1].islower():
        return False
    if punct.startswith(".") and not punct.startswith(".."):
        previous = paragraph[:match.start()].rsplit(" ", 1)[-1].lstrip("(\"'“‘").lower()
        # Abbreviations, initials ("A. Kumar") and dotted forms ("e.g.", "U.S.").
        if previous in _ABBREVIATIONS or len(previous) == 1 or "." in previous:
            return False
    return True


def split_sentences(text: str) -> list[str]:
    """Split text into sentences conservatively, keeping the original wording.

    Paragraphs (blank-line separated) always end a sentence; single line breaks
    inside a paragraph are treated as spaces.
    """
    sentences = []
    for paragraph in normalize_text(text).split("\n\n"):
        paragraph = paragraph.replace("\n", " ")
        start = 0
        for match in _BOUNDARY_RE.finditer(paragraph):
            if _is_boundary(paragraph, match):
                sentences.append(paragraph[start:match.end(1)])
                start = match.end()
        tail = paragraph[start:].strip()
        if tail:
            sentences.append(tail)
    return sentences


def tokenize_text(text: str) -> list[str]:
    """Return word and punctuation tokens for English and Hindi/Devanagari text."""
    return _TOKEN_RE.findall(text)
