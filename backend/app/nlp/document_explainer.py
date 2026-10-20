"""Combine simplification and information extraction into one explanation.

Everything here is built from the findings of the existing rule-based modules
and fixed per-language templates; nothing is generated or guessed.
"""

import unicodedata

from app.nlp.information_extraction import extract_information
from app.nlp.simplification import simplify_text
from app.nlp.text_processing import split_sentences

FACT_KEYS = ("deadlines", "dates", "fees", "eligibility", "required_documents", "action_items")

TEMPLATES = {
    "en": {
        "deadlines": "Deadline mentioned: {items}.",
        "other_dates": "Other dates mentioned (not marked as deadlines): {items}.",
        "fees": "Amounts mentioned: {items}.",
        "eligibility": "Eligibility condition stated: \"{items}\"",
        "eligibility_note": (
            "Samjho does not decide whether you are eligible; "
            "compare your own details with the condition above."
        ),
        "documents": "Documents mentioned: {items}.",
        "actions": "Actions mentioned: {items}.",
        "nothing": (
            "No supported deadlines, fees, eligibility conditions, documents or actions "
            "were found. Please read the original text."
        ),
        "unsupported": (
            "{count} sentence(s) are not covered by Samjho's rules and are shown unchanged."
        ),
        "check_eligibility": "Check whether you meet this condition: {source}",
        "check_document": "Keep this document ready: {value}",
        "check_action": "Complete this step: {source}",
        "check_fee": "Check this amount: {value}",
        "check_deadline": "Note the deadline: {value}",
    },
    "hi": {
        "deadlines": "समय सीमा: {items}।",
        "other_dates": "अन्य तिथियाँ (समय सीमा के रूप में चिह्नित नहीं): {items}।",
        "fees": "उल्लिखित राशि: {items}।",
        "eligibility": "पात्रता की शर्त: \"{items}\"",
        "eligibility_note": (
            "Samjho यह तय नहीं करता कि आप पात्र हैं या नहीं; "
            "अपनी जानकारी ऊपर दी गई शर्त से मिलाएं।"
        ),
        "documents": "उल्लिखित दस्तावेज़: {items}।",
        "actions": "उल्लिखित कार्य: {items}।",
        "nothing": (
            "कोई समर्थित समय सीमा, शुल्क, पात्रता शर्त, दस्तावेज़ या कार्य नहीं मिला। "
            "कृपया मूल पाठ पढ़ें।"
        ),
        "unsupported": "{count} वाक्य Samjho के नियमों में शामिल नहीं हैं और बिना बदलाव के दिखाए गए हैं।",
        "check_eligibility": "जाँचें कि आप यह शर्त पूरी करते हैं: {source}",
        "check_document": "यह दस्तावेज़ तैयार रखें: {value}",
        "check_action": "यह कदम पूरा करें: {source}",
        "check_fee": "यह राशि जाँचें: {value}",
        "check_deadline": "समय सीमा ध्यान रखें: {value}",
    },
    "hinglish": {
        "deadlines": "Deadline: {items}.",
        "other_dates": "Baaki tareekhein (deadline nahi maani gayi): {items}.",
        "fees": "Amount: {items}.",
        "eligibility": "Eligibility ki shart: \"{items}\"",
        "eligibility_note": (
            "Samjho yeh tay nahi karta ki aap eligible hain ya nahi; "
            "apni details upar di gayi shart se milayein."
        ),
        "documents": "Documents: {items}.",
        "actions": "Kaam: {items}.",
        "nothing": (
            "Koi supported deadline, fees, eligibility shart, document ya kaam nahi mila. "
            "Kripya original text padhein."
        ),
        "unsupported": "{count} vakya Samjho ke rules mein nahi aate aur bina badlav ke dikhaye gaye hain.",
        "check_eligibility": "Check karein ki aap yeh shart poori karte hain: {source}",
        "check_document": "Yeh document taiyaar rakhein: {value}",
        "check_action": "Yeh kadam poora karein: {source}",
        "check_fee": "Yeh amount check karein: {value}",
        "check_deadline": "Deadline yaad rakhein: {value}",
    },
}

# Date notes from the extractor, in each language. An unknown note is shown as-is.
DATE_NOTES = {
    "en": {},
    "hi": {
        "ambiguous day/month order": "दिन/महीने का क्रम स्पष्ट नहीं",
        "year not stated": "वर्ष नहीं दिया गया",
    },
    "hinglish": {
        "ambiguous day/month order": "din/mahine ka order saaf nahi",
        "year not stated": "saal nahi diya gaya",
    },
}


def _unique(values):
    seen, result = set(), []
    for value in values:
        if value.lower() not in seen:
            seen.add(value.lower())
            result.append(value)
    return result


def _date_text(finding, language):
    note = finding["note"]
    if not note:
        return finding["value"]
    return f"{finding['value']} ({DATE_NOTES[language].get(note, note)})"


def _explanation(facts, unsupported_count, language):
    t = TEMPLATES[language]
    lines = []
    deadline_keys = {(d["value"], d["source"]) for d in facts["deadlines"]}
    other_dates = [d for d in facts["dates"] if (d["value"], d["source"]) not in deadline_keys]

    if facts["deadlines"]:
        items = ", ".join(_date_text(d, language) for d in facts["deadlines"])
        lines.append(t["deadlines"].format(items=items))
    if other_dates:
        items = ", ".join(_date_text(d, language) for d in other_dates)
        lines.append(t["other_dates"].format(items=items))
    if facts["fees"]:
        lines.append(t["fees"].format(items=", ".join(f["value"] for f in facts["fees"])))
    for finding in facts["eligibility"]:
        lines.append(t["eligibility"].format(items=finding["source"]))
    if facts["eligibility"]:
        lines.append(t["eligibility_note"])
    if facts["required_documents"]:
        items = ", ".join(_unique(f["value"] for f in facts["required_documents"]))
        lines.append(t["documents"].format(items=items))
    if facts["action_items"]:
        items = ", ".join(_unique(f["value"] for f in facts["action_items"]))
        lines.append(t["actions"].format(items=items))

    if not lines:
        lines.append(t["nothing"])
    if unsupported_count:
        lines.append(t["unsupported"].format(count=unsupported_count))
    return lines


def _item(category, template, finding, value_text=None, needs_verification=False):
    return {
        "category": category,
        "task": template.format(value=value_text or finding["value"], source=finding["source"]),
        "value": finding["value"],
        "source": finding["source"],
        "needs_verification": needs_verification,
    }


def _checklist(facts, language):
    """Suggested steps, one per supported finding. Nothing is added without a finding."""
    t = TEMPLATES[language]
    items = [_item("eligibility", t["check_eligibility"], f) for f in facts["eligibility"]]

    seen_documents = set()
    for finding in facts["required_documents"]:
        if finding["value"].lower() not in seen_documents:
            seen_documents.add(finding["value"].lower())
            items.append(_item("required_documents", t["check_document"], finding))

    # One step per instruction sentence, even if it names several actions.
    actions_by_source = {}
    for finding in facts["action_items"]:
        actions_by_source.setdefault(finding["source"], []).append(finding["value"])
    for source, values in actions_by_source.items():
        finding = {"value": ", ".join(values), "source": source}
        items.append(_item("action_items", t["check_action"], finding))

    items += [_item("fees", t["check_fee"], f) for f in facts["fees"]]
    items += [
        _item("deadlines", t["check_deadline"], f, value_text=_date_text(f, language),
              needs_verification=f["iso"] is None)
        for f in facts["deadlines"]
    ]
    return items


def explain_document(text: str, language: str = "en") -> dict:
    """Simplify the text, extract facts, and build an explanation and checklist."""
    simplification = simplify_text(text, language)
    facts = extract_information(text, language)
    del facts["language"]

    sentences = []
    for sentence in split_sentences(unicodedata.normalize("NFC", text)):
        categories = [key for key in FACT_KEYS if any(f["source"] == sentence for f in facts[key])]
        simplified = simplify_text(sentence, language)["simplified_text"]
        if categories:
            status = "explained"
        elif simplified != sentence:
            status = "simplified_only"
        else:
            status = "unsupported"  # no rule applies: original wording kept, nothing invented
        sentences.append({
            "original": sentence, "simplified": simplified,
            "categories": categories, "status": status,
        })
    unsupported_count = sum(s["status"] == "unsupported" for s in sentences)

    return {
        "language": language,
        "original_text": text,
        "simplified_text": simplification["simplified_text"],
        "transformations": simplification["transformations"],
        "explanation": _explanation(facts, unsupported_count, language),
        "facts": facts,
        "checklist": _checklist(facts, language),
        "sentences": sentences,
    }
