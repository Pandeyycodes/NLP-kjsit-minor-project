"""Detect a negation word just before a match, so rules do not reverse its meaning.

"No applicant is required to submit" must not become "No applicant must submit",
and "Do not bring phones" must not become the action item "bring".
"""

import re

NEGATION_WORDS = {
    "en": {"no", "not", "never", "nobody", "none", "neither", "nor", "cannot"},
    "hi": {"न", "ना", "मत", "नहीं"},
    "hinglish": {"na", "mat", "nahi", "nahin", "nai"},
}
# How many words before a match to look at. English negation can sit a few
# words earlier ("No applicant is required to"); Hindi and Hinglish put it
# directly before the verb ("न लाएं", "mat bharein").
WINDOW = {"en": 3, "hi": 1, "hinglish": 1}

_CLAUSE_BREAK = re.compile(r"[.!?।;:,]")


def is_negated(text: str, start: int, language: str) -> bool:
    """True if a negation word appears in the same clause shortly before `start`."""
    clause = _CLAUSE_BREAK.split(text[:start])[-1]
    for word in clause.split()[-WINDOW[language]:]:
        word = word.strip("\"'“”‘’()").lower()
        if word in NEGATION_WORDS[language] or word.endswith(("n't", "n’t")):
            return True
    return False
