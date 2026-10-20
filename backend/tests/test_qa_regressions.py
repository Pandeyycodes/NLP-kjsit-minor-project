"""Regression tests for bugs found in the Step 8 quality-assurance audit."""

import pytest

from app.nlp.document_explainer import explain_document
from app.nlp.information_extraction import extract_information
from app.nlp.negation import is_negated
from app.nlp.simplification import simplify_text


def simplified(text, language="en"):
    return simplify_text(text, language)["simplified_text"]


def actions(text, language="en"):
    return [a["value"] for a in extract_information(text, language)["action_items"]]


# Bug 1: "No applicant is required to submit" became "No applicant must submit",
# turning "not required" into "not allowed".

@pytest.mark.parametrize("text", [
    "No applicant is required to submit a fee.",
    "Nobody is required to attend.",
    "Students who never obtain approval are dropped.",
])
def test_negated_phrases_are_not_simplified(text):
    result = simplify_text(text, "en")
    assert result["simplified_text"] == text
    assert result["transformations"] == []


def test_negation_only_affects_its_own_clause():
    assert simplified("Applicants are required to submit forms. No fee is charged.") == (
        "Applicants must submit forms. No fee is charged."
    )
    assert simplified("Do not panic, obtain assistance prior to Friday.") == (
        "Do not panic, get help before Friday."
    )


# Bug 2: "Do not bring phones" produced the action item "bring", and the
# checklist then told the user to complete it.

def test_negated_english_actions_are_not_action_items():
    text = "Do not bring mobile phones. Don't pay any agent. Never upload a photo. Bring your ID card."
    assert actions(text) == ["Bring"]


def test_negated_hindi_and_hinglish_actions_are_not_action_items():
    assert actions("मोबाइल फोन न लाएं। अंकपत्र साथ लाएं।", "hi") == ["साथ लाएं"]
    assert actions("Phone mat laayein. Form bharein.", "hinglish") == ["bharein"]


def test_checklist_has_no_step_for_a_prohibition():
    result = explain_document("Do not bring mobile phones.", "en")
    assert result["facts"]["action_items"] == []
    assert result["checklist"] == []


@pytest.mark.parametrize("text, word, language, expected", [
    ("Do not bring", "bring", "en", True),
    ("Students can't apply", "apply", "en", True),
    ("No, bring", "bring", "en", False),          # the comma ends the negated clause
    ("Note the rules and bring", "bring", "en", False),
    ("फोन न लाएं", "लाएं", "hi", True),
    ("फोन साथ लाएं", "लाएं", "hi", False),
    ("form mat bharein", "bharein", "hinglish", True),
])
def test_is_negated(text, word, language, expected):
    assert is_negated(text, text.index(word), language) is expected


# Bug 3: "₹1.5 lakh" was extracted as "₹1.5" with amount 1.5.
# Bug 4: "Rs. 500-1000" was extracted as "Rs. 500".

@pytest.mark.parametrize("text, value, amount, amount_max", [
    ("Stipend of ₹1.5 lakh per year.", "₹1.5 lakh", 150_000, None),
    ("Package: ₹6 LPA.", "₹6 LPA", 600_000, None),
    ("Fine of Rs 2.3 crore.", "Rs 2.3 crore", 23_000_000, None),
    ("Bonus of ₹50k.", "₹50k", 50_000, None),
    ("A grant of 2 lakh rupees.", "2 lakh rupees", 200_000, None),
    ("शुल्क ₹२ हज़ार है।", "₹२ हज़ार", 2_000, None),
    ("Fee Rs. 500-1000.", "Rs. 500-1000", 500, 1000),
    ("Fee ₹1–2 lakh.", "₹1–2 lakh", 100_000, 200_000),
    ("Fee Rs 1,500/- only.", "Rs 1,500/-", 1500, None),
])
def test_amount_words_and_ranges_are_kept(text, value, amount, amount_max):
    [fee] = extract_information(text)["fees"]
    assert (fee["value"], fee["amount"], fee["amount_max"]) == (value, amount, amount_max)


def test_unit_must_be_a_whole_word():
    [fee] = extract_information("Rice for ₹5 kids and Rs 2 credits.")["fees"][:1]
    assert fee["value"] == "₹5"
    assert [f["value"] for f in extract_information("Rs 2 credits.")["fees"]] == ["Rs 2"]


GROUNDING_SAMPLES = [
    ("en", (
        "Applicants are required to submit the requisite documents prior to 30/11/2026. "
        "Eligible candidates with at least 60% marks may apply. The fee is Rs. 500-1000 "
        "and the stipend is ₹1.5 lakh. Bring your marksheet, college ID and passport-size "
        "photographs. Do not bring mobile phones. The college was founded on 15 August 1960. "
        "Exam on 05/11/2026 and results by 20 December."
    )),
    ("hi", (
        "आवेदन की अंतिम तिथि 15 नवंबर 2026 है। न्यूनतम 60% अंक वाले अभ्यर्थी पात्र हैं। "
        "आवेदन शुल्क ₹500 है। अंकपत्र और पहचान पत्र साथ लाएं। मोबाइल फोन न लाएं। "
        "फॉर्म ३० नवंबर २०२६ तक ऑनलाइन जमा करें।"
    )),
    ("hinglish", (
        "Avedan ki antim tithi 15/11/2026 hai. Kam se kam 60% marks wale students eligible "
        "hain. Fees Rs. 500 hai. Resume aur aadhaar card upload karein. Phone mat laayein."
    )),
]


@pytest.mark.parametrize("language, text", GROUNDING_SAMPLES)
def test_every_finding_is_grounded_in_the_document(language, text):
    import unicodedata

    def squash(value):
        return " ".join(unicodedata.normalize("NFC", value).split())

    document = squash(text)
    result = explain_document(text, language)
    findings = [f for key in result["facts"] for f in result["facts"][key]]
    assert findings, "sample should produce findings"
    for finding in findings:
        assert squash(finding["source"]) in document
        assert squash(finding["value"]) in squash(finding["source"])
    sources = {f["source"] for f in findings}
    for item in result["checklist"]:
        assert item["source"] in sources
    for sentence in result["sentences"]:
        assert squash(sentence["original"]) in document


def test_explanation_shows_the_full_amount():
    result = explain_document("The stipend is ₹1.5 lakh per year.", "en")
    assert "Amounts mentioned: ₹1.5 lakh." in result["explanation"]
