import pytest

from app.nlp.information_extraction import extract_information


def values(result, key):
    return [finding["value"] for finding in result[key]]


# Dates

@pytest.mark.parametrize("text, value, iso", [
    ("Exam on 15 November 2026.", "15 November 2026", "2026-11-15"),
    ("Exam on 15th Nov, 2026.", "15th Nov, 2026", "2026-11-15"),
    ("Exam on 15/11/2026.", "15/11/2026", "2026-11-15"),
    ("Exam on 15-11-2026.", "15-11-2026", "2026-11-15"),
    ("Exam on 2026-11-15.", "2026-11-15", "2026-11-15"),
    ("Exam on November 15, 2026.", "November 15, 2026", "2026-11-15"),
])
def test_supported_date_formats(text, value, iso):
    dates = extract_information(text)["dates"]
    assert len(dates) == 1
    assert dates[0]["value"] == value
    assert dates[0]["iso"] == iso
    assert dates[0]["note"] is None
    assert dates[0]["source"] == text


def test_ambiguous_numeric_date_is_not_resolved():
    [found] = extract_information("Exam on 05/11/2026.")["dates"]
    assert found["iso"] is None
    assert found["note"] == "ambiguous day/month order"


def test_missing_year_is_not_invented():
    [found] = extract_information("Exam on 15 November.")["dates"]
    assert found["value"] == "15 November"
    assert found["iso"] is None
    assert found["note"] == "year not stated"


def test_invalid_dates_and_lowercase_may_are_ignored():
    text = "Invalid 31/02/2026 and 45/13/2026. Students aged 18 may apply."
    assert extract_information(text)["dates"] == []


# Deadlines

def test_deadline_versus_historical_dates():
    text = (
        "The college was established on 15 August 1960. "
        "Submit your resume by 15 November 2026."
    )
    result = extract_information(text)
    assert values(result, "dates") == ["15 August 1960", "15 November 2026"]
    [deadline] = result["deadlines"]
    assert deadline["value"] == "15 November 2026"
    assert deadline["cue"] == "by"
    assert deadline["rule"] == "deadline_cue"


def test_deadline_keyword_only_applies_to_following_date():
    text = "Results were declared on 2025-05-10 and the last date to apply is 30/11/2026."
    result = extract_information(text)
    assert len(result["dates"]) == 2
    assert values(result, "deadlines") == ["30/11/2026"]
    assert result["deadlines"][0]["cue"] == "last date"


def test_unrelated_date_is_not_a_deadline():
    result = extract_information("The workshop was held on 10 March 2025.")
    assert len(result["dates"]) == 1
    assert result["deadlines"] == []


# Fees

@pytest.mark.parametrize("text, value, amount", [
    ("The fee is ₹500.", "₹500", 500),
    ("The fee is ₹ 1,200.50 only.", "₹ 1,200.50", 1200.5),
    ("The fee is Rs. 500.", "Rs. 500", 500),
    ("The fee is Rs 1,500/- per year.", "Rs 1,500/-", 1500),
    ("The fee is INR 2,00,000.", "INR 2,00,000", 200000),
    ("The fee is 300 rupees.", "300 rupees", 300),
    ("शुल्क 500 रुपये है।", "500 रुपये", 500),
])
def test_rupee_amounts(text, value, amount):
    [fee] = extract_information(text)["fees"]
    assert fee["value"] == value
    assert fee["amount"] == amount
    assert fee["currency"] == "INR"
    assert fee["source"] == text


def test_plain_numbers_are_not_fees():
    result = extract_information("Room 500 has 60% seats for 2 hrs 30 minutes.")
    assert result["fees"] == []


# Eligibility

@pytest.mark.parametrize("text, value", [
    ("Students with at least 60% marks can apply.", "at least 60% marks"),
    ("A minimum 60% marks is needed.", "minimum 60% marks"),
    ("Only eligible candidates will be called.", "eligible"),
    ("You must be a final-year student.", "must be a final-year student"),
])
def test_eligibility_statements(text, value):
    [found] = extract_information(text)["eligibility"]
    assert found["value"] == value
    assert found["source"] == text


# Documents and actions

def test_multiple_required_documents():
    text = (
        "Bring your college ID, marksheets, passport-size photographs and identity proof. "
        "Attach a resume."
    )
    assert values(extract_information(text), "required_documents") == [
        "college ID", "marksheets", "passport-size photographs", "identity proof", "resume",
    ]


def test_multiple_action_items():
    text = "Register online, upload the form and pay the fee. Attend the interview."
    assert values(extract_information(text), "action_items") == [
        "Register", "upload", "pay", "Attend",
    ]


def test_nouns_are_not_action_items():
    assert extract_information("The pay is good and your report is ready.")["action_items"] == []


# Hindi

def test_hindi_extraction():
    text = (
        "आवेदन की अंतिम तिथि 15 नवंबर 2026 है। न्यूनतम 60% अंक वाले छात्र पात्र हैं। "
        "आवेदन शुल्क ₹500 है। अंकपत्र और पहचान पत्र साथ लाएं। "
        "फॉर्म ३० नवंबर २०२६ तक ऑनलाइन जमा करें। 15 अगस्त 1947 को आज़ादी मिली।"
    )
    result = extract_information(text, "hi")
    assert [d["iso"] for d in result["dates"]] == ["2026-11-15", "2026-11-30", "1947-08-15"]
    assert [(d["value"], d["cue"]) for d in result["deadlines"]] == [
        ("15 नवंबर 2026", "अंतिम तिथि"), ("३० नवंबर २०२६", "तक"),
    ]
    assert values(result, "fees") == ["₹500"]
    assert values(result, "eligibility") == ["न्यूनतम 60% अंक"]
    assert values(result, "required_documents") == ["अंकपत्र", "पहचान पत्र"]
    assert values(result, "action_items") == ["साथ लाएं", "जमा करें"]


def test_hindi_certificate_documents():
    result = extract_information("जाति प्रमाण पत्र और आधार कार्ड अपलोड करें।", "hi")
    assert values(result, "required_documents") == ["जाति प्रमाण पत्र", "आधार कार्ड"]
    assert values(result, "action_items") == ["अपलोड करें"]


# Hinglish

def test_hinglish_extraction():
    text = (
        "Avedan ki antim tithi 15/11/2026 hai. Kam se kam 60% marks wale students "
        "eligible hain. Fees Rs. 500 hai. Resume aur aadhaar card upload karein. "
        "20 Nov 2026 tak interview mein upasthit rahein."
    )
    result = extract_information(text, "hinglish")
    assert [(d["value"], d["cue"]) for d in result["deadlines"]] == [
        ("15/11/2026", "antim tithi"), ("20 Nov 2026", "tak"),
    ]
    assert [f["amount"] for f in result["fees"]] == [500]
    assert values(result, "eligibility") == ["Kam se kam 60% marks"]
    assert values(result, "required_documents") == ["Resume", "aadhaar card"]
    assert values(result, "action_items") == ["upload karein", "upasthit rahein"]


# No matches and validation

@pytest.mark.parametrize("language", ["en", "hi", "hinglish"])
def test_text_without_supported_patterns(language):
    result = extract_information("The library opens at 9 AM on weekdays.", language)
    assert result["language"] == language
    for key in ["deadlines", "dates", "fees", "eligibility", "required_documents", "action_items"]:
        assert result[key] == []


def test_invalid_language_raises():
    with pytest.raises(ValueError):
        extract_information("Submit by 15 November 2026.", "fr")
