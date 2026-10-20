"""Rule-based phrase simplification for English, Hindi and Hinglish."""

import json
import re
import unicodedata
from pathlib import Path

from app.nlp.negation import is_negated
from app.nlp.text_processing import WORD_CHAR

LANGUAGES = ("en", "hi", "hinglish")
RULES_DIR = Path(__file__).parent


def _normalize(text: str) -> str:
    # NFC makes the same visible Devanagari letter (e.g. ज़ typed as one or two
    # code points) compare equal.
    return unicodedata.normalize("NFC", text)


def load_rules(language: str) -> dict[str, str]:
    """Load one language's phrase dictionary, keyed by lowercase phrase."""
    path = RULES_DIR / f"phrase_rules_{language}.json"
    with path.open(encoding="utf-8") as file:
        return {
            _normalize(phrase).lower(): _normalize(replacement)
            for phrase, replacement in json.load(file).items()
        }


def _build_pattern(phrases) -> re.Pattern:
    # Longest phrases first, so "is required to submit" wins over "is required to".
    # Words inside a phrase may be separated by any whitespace (including line breaks).
    alternatives = [
        r"\s+".join(re.escape(word) for word in phrase.split())
        for phrase in sorted(phrases, key=len, reverse=True)
    ]
    # Python's \b ignores Devanagari vowel signs, so build word boundaries from
    # the same word-character class the tokenizer uses.
    return re.compile(
        rf"(?<!{WORD_CHAR})(?:" + "|".join(alternatives) + rf")(?!{WORD_CHAR})",
        re.IGNORECASE,
    )


RULES = {language: load_rules(language) for language in LANGUAGES}
PATTERNS = {language: _build_pattern(RULES[language]) for language in LANGUAGES}


def _match_case(original: str, replacement: str) -> str:
    """Copy the capitalization style of the matched text onto the replacement."""
    if original.isupper() and len(original) > 1:
        return replacement.upper()
    if original[0].isupper():
        return replacement[0].upper() + replacement[1:]
    return replacement


def simplify_text(text: str, language: str = "en") -> dict:
    """Simplify text using only the selected language's rules."""
    if language not in LANGUAGES:
        raise ValueError(f"Unsupported language: {language}")
    rules = RULES[language]
    transformations = []

    def replace(match: re.Match) -> str:
        original = match.group(0)
        if is_negated(match.string, match.start(), language):
            return original  # e.g. "No one is required to" must not become "No one must"
        key = " ".join(original.lower().split())
        replacement = _match_case(original, rules[key])
        transformations.append(
            {"original": original, "replacement": replacement, "start": match.start()}
        )
        return replacement

    simplified = PATTERNS[language].sub(replace, _normalize(text))
    return {
        "language": language,
        "original_text": text,
        "simplified_text": simplified,
        "transformations": transformations,
        "transformation_count": len(transformations),
    }
