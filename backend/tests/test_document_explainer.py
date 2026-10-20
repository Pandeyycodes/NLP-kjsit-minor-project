import pytest

from app.nlp.document_explainer import FACT_KEYS, TEMPLATES, explain_document

FULL = (
    "Students with at least 60% marks must submit their resume by 15 November 2026. "
    "The application fee is ₹500."
)
FIRST, SECOND = (
    "Students with at least 60% marks must submit their resume by 15 November 2026.",
    "The application fee is ₹500.",
)


def test_full_document():
    result = explain_document(FULL, "en")
    assert result["original_text"] == FULL
    assert result["simplified_text"] == FULL  # no simplification rule applies
    assert result["explanation"] == [
        "Deadline mentioned: 15 November 2026.",
        "Amounts mentioned: ₹500.",
        f'Eligibility condition stated: "{FIRST}"',
        TEMPLATES["en"]["eligibility_note"],
        "Documents mentioned: resume.",
        "Actions mentioned: submit.",
    ]
    assert [(i["category"], i["task"]) for i in result["checklist"]] == [
        ("eligibility", f"Check whether you meet this condition: {FIRST}"),
        ("required_documents", "Keep this document ready: resume"),
        ("action_items", f"Complete this step: {FIRST}"),
        ("fees", "Check this amount: ₹500"),
        ("deadlines", "Note the deadline: 15 November 2026"),
    ]
    assert [s["status"] for s in result["sentences"]] == ["explained", "explained"]


def test_partial_document_only_reports_what_is_present():
    result = explain_document("The application fee is ₹500.", "en")
    assert result["explanation"] == ["Amounts mentioned: ₹500."]
    assert [i["category"] for i in result["checklist"]] == ["fees"]
    for key in ("deadlines", "dates", "eligibility", "required_documents", "action_items"):
        assert result["facts"][key] == []


def test_document_without_recognised_patterns():
    text = "The library opens at 9 AM."
    result = explain_document(text, "en")
    assert result["simplified_text"] == text
    assert result["checklist"] == []
    assert result["explanation"] == [
        TEMPLATES["en"]["nothing"],
        TEMPLATES["en"]["unsupported"].format(count=1),
    ]
    assert result["sentences"] == [
        {"original": text, "simplified": text, "categories": [], "status": "unsupported"}
    ]


def test_unrelated_date_is_not_a_deadline():
    result = explain_document("The college was founded on 15 August 1960.", "en")
    assert result["facts"]["deadlines"] == []
    assert result["explanation"][0] == (
        "Other dates mentioned (not marked as deadlines): 15 August 1960."
    )
    assert result["checklist"] == []


def test_incomplete_dates_need_verification():
    result = explain_document("Submit by 05/11/2026. Register by 15 November.", "en")
    deadlines = [i for i in result["checklist"] if i["category"] == "deadlines"]
    assert [(i["task"], i["needs_verification"]) for i in deadlines] == [
        ("Note the deadline: 05/11/2026 (ambiguous day/month order)", True),
        ("Note the deadline: 15 November (year not stated)", True),
    ]
    assert all(i["value"] in ("05/11/2026", "15 November") for i in deadlines)


def test_simplified_only_and_unsupported_sentences():
    text = "Applicants are required to obtain assistance prior to joining. The library opens at 9 AM."
    result = explain_document(text, "en")
    assert result["simplified_text"] == (
        "Applicants must get help before joining. The library opens at 9 AM."
    )
    assert [s["status"] for s in result["sentences"]] == ["simplified_only", "unsupported"]
    assert len(result["transformations"]) == 4


def test_checklist_matches_findings():
    text = (
        "Eligible candidates must register online. Bring your marksheet and college ID. "
        "Upload your resume and pay Rs. 200 by 30/11/2026. The pay is good."
    )
    result = explain_document(text, "en")
    facts = result["facts"]
    sources = {f["source"] for key in FACT_KEYS for f in facts[key]}
    for item in result["checklist"]:
        assert item["source"] in sources
    by_category = {}
    for item in result["checklist"]:
        by_category.setdefault(item["category"], []).append(item)
    assert len(by_category["eligibility"]) == len(facts["eligibility"]) == 1
    assert [i["value"] for i in by_category["required_documents"]] == [
        "marksheet", "college ID", "resume",
    ]
    # one step per instruction sentence; "The pay is good." is not an action
    assert [i["value"] for i in by_category["action_items"]] == [
        "register", "Bring", "Upload, pay",
    ]
    assert [i["value"] for i in by_category["fees"]] == ["Rs. 200"]
    assert [i["value"] for i in by_category["deadlines"]] == ["30/11/2026"]


def test_never_claims_the_user_is_eligible():
    result = explain_document("Only eligible candidates may apply.", "en")
    note = TEMPLATES["en"]["eligibility_note"]
    assert note in result["explanation"]
    lines = [line for line in result["explanation"] if line != note]
    text = " ".join(lines + [i["task"] for i in result["checklist"]]).lower()
    assert "you are eligible" not in text


def test_hindi_output():
    text = (
        "आवेदन की अंतिम तिथि 15 नवंबर 2026 है। न्यूनतम 60% अंक वाले छात्र पात्र हैं। "
        "अंकपत्र साथ लाएं। पुस्तकालय सुबह खुलता है।"
    )
    result = explain_document(text, "hi")
    assert result["simplified_text"].startswith("आवेदन की आखिरी तारीख 15 नवंबर 2026 है।")
    assert result["explanation"] == [
        "समय सीमा: 15 नवंबर 2026।",
        'पात्रता की शर्त: "न्यूनतम 60% अंक वाले छात्र पात्र हैं।"',
        TEMPLATES["hi"]["eligibility_note"],
        "उल्लिखित दस्तावेज़: अंकपत्र।",
        "उल्लिखित कार्य: साथ लाएं।",
        TEMPLATES["hi"]["unsupported"].format(count=1),
    ]
    assert [i["task"] for i in result["checklist"]] == [
        "जाँचें कि आप यह शर्त पूरी करते हैं: न्यूनतम 60% अंक वाले छात्र पात्र हैं।",
        "यह दस्तावेज़ तैयार रखें: अंकपत्र",
        "यह कदम पूरा करें: अंकपत्र साथ लाएं।",
        "समय सीमा ध्यान रखें: 15 नवंबर 2026",
    ]
    assert result["sentences"][-1]["status"] == "unsupported"
    assert result["sentences"][-1]["original"] == "पुस्तकालय सुबह खुलता है।"


def test_hindi_date_note_is_localised():
    result = explain_document("अंतिम तिथि 15 नवंबर है।", "hi")
    assert result["explanation"][0] == "समय सीमा: 15 नवंबर (वर्ष नहीं दिया गया)।"


def test_hinglish_output():
    result = explain_document("Antim tithi 15 Nov hai. Resume upload karein.", "hinglish")
    assert result["simplified_text"] == "Last date 15 Nov hai. Resume upload karein."
    assert result["explanation"] == [
        "Deadline: 15 Nov (saal nahi diya gaya).",
        "Documents: Resume.",
        "Kaam: upload karein.",
    ]
    assert [(i["task"], i["needs_verification"]) for i in result["checklist"]] == [
        ("Yeh document taiyaar rakhein: Resume", False),
        ("Yeh kadam poora karein: Resume upload karein.", False),
        ("Deadline yaad rakhein: 15 Nov (saal nahi diya gaya)", True),
    ]


@pytest.mark.parametrize("language", ["en", "hi", "hinglish"])
def test_output_is_deterministic(language):
    text = FULL + " अंतिम तिथि 15 नवंबर 2026 है। Resume upload karein."
    assert explain_document(text, language) == explain_document(text, language)


def test_invalid_language_raises():
    with pytest.raises(ValueError):
        explain_document(FULL, "fr")
