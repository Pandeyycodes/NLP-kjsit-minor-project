"""Rule-based information extraction: dates, deadlines, fees, eligibility,
documents and action items. Every finding comes from a regular-expression rule
and keeps the sentence it was found in, so it can be checked by a person."""

import re
import unicodedata
from datetime import date

from app.nlp.text_processing import WORD_CHAR, split_sentences

LANGUAGES = ("en", "hi", "hinglish")

# Word boundaries that also work for Devanagari (Python's \b does not).
_START = rf"(?<!{WORD_CHAR})"
_END = rf"(?!{WORD_CHAR})"


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _phrase_pattern(phrases, plural=False) -> re.Pattern:
    """Match any of the literal phrases as whole words; spaces/hyphens are interchangeable."""
    alternatives = [
        r"[\s-]+".join(re.escape(word) for word in re.split(r"[\s-]+", _nfc(phrase)))
        for phrase in sorted(phrases, key=len, reverse=True)
    ]
    suffix = "s?" if plural else ""
    return re.compile(rf"{_START}(?:{'|'.join(alternatives)}){suffix}{_END}", re.IGNORECASE)


def _regex_pattern(regexes) -> re.Pattern:
    """Match any of the regular expressions as whole words."""
    return re.compile(rf"{_START}(?:{'|'.join(_nfc(r) for r in regexes)}){_END}", re.IGNORECASE)


# ---------------------------------------------------------------- dates

_EN_MONTHS = [
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
]
_HI_MONTHS = {
    "जनवरी": 1, "फ़रवरी": 2, "फरवरी": 2, "मार्च": 3, "अप्रैल": 4, "मई": 5, "जून": 6,
    "जुलाई": 7, "अगस्त": 8, "सितंबर": 9, "सितम्बर": 9, "अक्टूबर": 10, "अक्तूबर": 10,
    "नवंबर": 11, "नवम्बर": 11, "दिसंबर": 12, "दिसम्बर": 12,
}

# English month names must be capitalised ("May", "MAY") so the verb "may" is not a date.
MONTHS = {_nfc(name): number for name, number in _HI_MONTHS.items()}
for _number, _name in enumerate(_EN_MONTHS, start=1):
    for _form in (_name, _name[:3]):
        MONTHS[_form.title()] = MONTHS[_form.upper()] = _number
MONTHS["Sept"] = MONTHS["SEPT"] = 9

_MONTH = "(?P<mon>" + "|".join(sorted(map(re.escape, MONTHS), key=len, reverse=True)) + ")"
_DAY = r"(?P<d>\d{1,2})(?!\d)(?:st|nd|rd|th)?"
_YEAR = r"(?P<y>\d{4})(?!\d)"

DATE_PATTERNS = [
    # 2026-11-15
    ("date_iso", re.compile(rf"(?<!\d){_YEAR}-(?P<m>\d{{1,2}})-(?P<d>\d{{1,2}})(?!\d)")),
    # 15/11/2026, 15-11-2026, 15.11.2026
    ("date_numeric", re.compile(
        rf"(?<!\d)(?P<a>\d{{1,2}})(?P<sep>[/.-])(?P<b>\d{{1,2}})(?P=sep){_YEAR}"
    )),
    # 15 November 2026, 15th Nov, 2026, 15 नवंबर 2026, 15 November (no year)
    ("date_day_month_year", re.compile(
        rf"(?<!\d){_DAY}\s+(?:of\s+)?{_MONTH}{_END}(?:\.?,?\s+{_YEAR})?"
    )),
    # November 15, 2026
    ("date_month_day_year", re.compile(rf"{_START}{_MONTH}\.?\s+{_DAY},?\s+{_YEAR}")),
]


def _parse_date(rule: str, match: re.Match):
    """Return (iso_date_or_None, note_or_None), or None if it is not a real calendar date."""
    if rule == "date_numeric":
        a, b, year = int(match["a"]), int(match["b"]), int(match["y"])
        if min(a, b) < 1:
            return None
        if a > 12 and b <= 12:
            day, month = a, b
        elif b > 12 and a <= 12:
            month, day = a, b
        elif a == b:
            day = month = a
        elif a <= 12 and b <= 12:
            # 05/11/2026 could be 5 November or May 11: do not guess.
            return None, "ambiguous day/month order"
        else:
            return None
    else:
        day = int(match["d"])
        month = int(match["m"]) if rule == "date_iso" else MONTHS[match["mon"]]
        year = int(match["y"]) if match["y"] else None
    try:
        parsed = date(year or 2000, month, day)  # 2000 is a leap year, so 29 Feb passes
    except ValueError:
        return None
    if year is None:
        return None, "year not stated"
    return parsed.isoformat(), None


def _non_overlapping(patterns, text):
    """All (rule, match) pairs from several patterns, earliest first, skipping overlaps."""
    found = [(rule, m) for rule, pattern in patterns for m in pattern.finditer(text)]
    found.sort(key=lambda item: (item[1].start(), -item[1].end()))
    result, last_end = [], -1
    for rule, match in found:
        if match.start() >= last_end:
            result.append((rule, match))
            last_end = match.end()
    return result


# -------------------------------------------------------------- deadlines

# A date is a deadline only if (a) a deadline keyword appears before it in the
# same sentence (and after any earlier date), or (b) a word like "by"/"तक" is
# directly next to it.
_DEADLINE_KEYWORDS = {
    "en": ["deadline", "last date", "due date", "closing date", "last day", "closes"],
    "hi": ["अंतिम तिथि", "अंतिम तारीख", "अंतिम दिनांक", "आखिरी तारीख", "समय सीमा"],
    "hinglish": ["deadline", "last date", "due date", "antim tithi", "aakhri tareekh",
                 "akhri tareekh"],
}
_DEADLINE_WORDS_BEFORE_DATE = {
    "en": ["by", "before", "until", "till", "on or before", "no later than"],
    "hi": [],
    "hinglish": ["by", "before", "until", "till"],
}
_DEADLINE_WORDS_AFTER_DATE = {
    "en": [],
    "hi": ["तक", "से पहले", "से पूर्व"],
    "hinglish": ["tak", "se pehle", "se purv", "se poorv"],
}


def _alternatives(phrases):
    return "|".join(r"\s+".join(map(re.escape, _nfc(p).split())) for p in phrases)


_DEADLINE_RULES = {
    language: {
        "keyword": _phrase_pattern(_DEADLINE_KEYWORDS[language]),
        "before": re.compile(
            rf"{_START}(?:{_alternatives(_DEADLINE_WORDS_BEFORE_DATE[language])})\s+(?:the\s+)?$",
            re.IGNORECASE,
        ) if _DEADLINE_WORDS_BEFORE_DATE[language] else None,
        "after": re.compile(
            rf"^\s*(?:{_alternatives(_DEADLINE_WORDS_AFTER_DATE[language])}){_END}",
            re.IGNORECASE,
        ) if _DEADLINE_WORDS_AFTER_DATE[language] else None,
    }
    for language in LANGUAGES
}


def _deadline_cue(sentence: str, match: re.Match, previous_end: int, language: str):
    """Return the wording that marks this date as a deadline, or None."""
    rules = _DEADLINE_RULES[language]
    keyword = rules["keyword"].search(sentence, previous_end, match.start())
    if keyword:
        return keyword.group(0)
    if rules["before"]:
        nearby = rules["before"].search(sentence[:match.start()])
        if nearby:
            return nearby.group(0).strip()
    if rules["after"]:
        nearby = rules["after"].search(sentence[match.end():])
        if nearby:
            return nearby.group(0).strip()
    return None


# ------------------------------------------------------------------- fees

_AMOUNT = r"(?P<amount>\d+(?:,\d+)*(?:\.\d+)?)"
FEE_PATTERNS = [
    # ₹500, Rs. 500, Rs 1,500/-, INR 500, रु. 500
    ("currency_before_amount", re.compile(
        rf"(?:₹|{_START}(?:rs|inr|रु|रू)\.?)\s*{_AMOUNT}(?:\s*/-)?", re.IGNORECASE
    )),
    # 500 rupees, 500 रुपये
    ("amount_before_currency", re.compile(
        rf"(?<![\d,.]){_AMOUNT}\s*(?:/-\s*)?(?:rupees|rupaye|rupaiye|रुपये|रुपए|रुपया){_END}",
        re.IGNORECASE,
    )),
]


def _to_number(amount: str):
    number = float(amount.replace(",", ""))
    return int(number) if number.is_integer() else number


# ----------------------------------------- eligibility, documents, actions

_PERCENT = r"\d+(?:\.\d+)?\s*(?:%|percent)"

ELIGIBILITY_PATTERNS = {
    "en": _regex_pattern([
        rf"(?:minimum|at least|min\.?)\s+(?:of\s+)?{_PERCENT}(?:\s+(?:marks|aggregate))?",
        rf"{_PERCENT}\s+(?:marks|aggregate)",
        r"eligib(?:le|ility)",
        r"must be (?:a|an)\s+(?:[\w-]+\s+){0,3}?students?",
        r"cgpa", r"age limit", r"years of age", r"open only to",
    ]),
    "hi": _regex_pattern([
        rf"(?:न्यूनतम|कम से कम)\s+{_PERCENT}(?:\s+अंक)?",
        rf"{_PERCENT}\s+अंक",
        "पात्रता", "पात्र", "योग्यता", "योग्य", "आयु सीमा",
    ]),
    "hinglish": _regex_pattern([
        rf"(?:nyuntam|kam se kam|minimum|at least)\s+{_PERCENT}(?:\s+(?:marks|ank))?",
        rf"{_PERCENT}\s+(?:marks|ank)",
        r"eligib(?:le|ility)", "patrata", "yogyata", "yogya", "age limit", "aayu seema",
    ]),
}

DOCUMENT_PATTERNS = {
    "en": _phrase_pattern([
        "resume", "cv", "curriculum vitae", "biodata", "marksheet", "mark sheet",
        "transcript", "college id", "college id card", "id card", "identity card",
        "identity proof", "id proof", "address proof", "passport size photograph",
        "passport size photo", "photograph", "photo", "aadhaar card", "aadhar card",
        "pan card", "bonafide certificate", "caste certificate", "income certificate",
        "domicile certificate", "leaving certificate", "no objection certificate",
        "fee receipt", "cover letter", "offer letter",
    ], plural=True),
    "hi": _phrase_pattern([
        "प्रमाण पत्र", "प्रमाणपत्र", "जाति प्रमाण पत्र", "आय प्रमाण पत्र", "निवास प्रमाण पत्र",
        "अंकपत्र", "अंक पत्र", "अंकसूची", "पहचान पत्र", "आधार कार्ड", "पैन कार्ड",
        "पासपोर्ट साइज़ फ़ोटो", "पासपोर्ट साइज फोटो", "फ़ोटो", "फोटो", "बायोडाटा",
        "रिज्यूमे", "शुल्क रसीद",
    ]),
    "hinglish": _phrase_pattern([
        "resume", "cv", "biodata", "marksheet", "mark sheet", "ank patra", "ankpatra",
        "praman patra", "pramanpatra", "jati praman patra", "aay praman patra",
        "niwas praman patra", "pehchan patra", "id card", "college id", "id proof",
        "aadhaar card", "aadhar card", "pan card", "passport size photo", "photo",
        "fee receipt", "shulk raseed",
    ], plural=True),
}

ACTION_PATTERNS = {
    "en": _phrase_pattern([
        "submit", "register", "upload", "attend", "pay", "bring", "apply", "fill",
        "carry", "send", "download", "enrol", "enroll",
    ]),
    "hi": _regex_pattern([
        r"(?:जमा|पंजीकरण|रजिस्टर|अपलोड|भुगतान|आवेदन|डाउनलोड)\s+(?:करें|करना|कीजिए|करे|करो|कराएं)",
        r"उपस्थित\s+(?:हों|रहें|होना|रहना)",
        r"(?:साथ\s+)?लेकर\s+आएं", r"(?:साथ\s+)?लाएं", "भरें",
    ]),
    "hinglish": _regex_pattern([
        r"(?:jama|submit|register|upload|attend|pay|apply|fill|download|bhugtan|panjikaran)"
        r"\s+(?:karein|karen|karna|kare|kijiye|karo)",
        r"upasthit\s+(?:rahein|rahen|rahe|hona|rahna)",
        r"(?:saath\s+)?lekar\s+(?:aayein|aaye|aana)", r"bhar(?:ein|en|na)",
    ]),
}

# "the pay", "your report": an English verb after a determiner is being used as a noun.
_DETERMINER_BEFORE = re.compile(
    r"\b(?:the|a|an|your|their|our|his|her|its|this|that|my)\s+$", re.IGNORECASE
)


def _findings(pattern, sentence, rule, skip=None):
    """Every distinct match of `pattern` in the sentence, with the sentence as its source."""
    findings, seen = [], set()
    for match in pattern.finditer(sentence):
        value = match.group(0)
        if (skip and skip(sentence, match)) or value.lower() in seen:
            continue
        seen.add(value.lower())
        findings.append({"value": value, "rule": rule, "source": sentence})
    return findings


def _is_noun_use(sentence, match):
    return bool(_DETERMINER_BEFORE.search(sentence[:match.start()]))


# ------------------------------------------------------------------- main

def extract_information(text: str, language: str = "en") -> dict:
    """Extract dates, deadlines, fees, eligibility, documents and action items."""
    if language not in LANGUAGES:
        raise ValueError(f"Unsupported language: {language}")
    result = {
        "language": language,
        "deadlines": [], "dates": [], "fees": [], "eligibility": [],
        "required_documents": [], "action_items": [],
    }
    for sentence in split_sentences(_nfc(text)):
        previous_end = 0
        for rule, match in _non_overlapping(DATE_PATTERNS, sentence):
            parsed = _parse_date(rule, match)
            if parsed is None:
                continue
            iso, note = parsed
            finding = {"value": match.group(0), "iso": iso, "note": note,
                       "rule": rule, "source": sentence}
            result["dates"].append(finding)
            cue = _deadline_cue(sentence, match, previous_end, language)
            if cue:
                result["deadlines"].append({**finding, "rule": "deadline_cue", "cue": cue})
            previous_end = match.end()

        for rule, match in _non_overlapping(FEE_PATTERNS, sentence):
            result["fees"].append({
                "value": match.group(0), "amount": _to_number(match["amount"]),
                "currency": "INR", "rule": rule, "source": sentence,
            })

        eligibility = ELIGIBILITY_PATTERNS[language].search(sentence)
        if eligibility:
            result["eligibility"].append(
                {"value": eligibility.group(0), "rule": "eligibility_phrase", "source": sentence}
            )

        result["required_documents"] += _findings(
            DOCUMENT_PATTERNS[language], sentence, "document_name"
        )
        result["action_items"] += _findings(
            ACTION_PATTERNS[language], sentence, "action_phrase",
            skip=_is_noun_use if language == "en" else None,
        )
    return result
