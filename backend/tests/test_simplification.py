import unicodedata

import pytest

from app.nlp.simplification import LANGUAGES, RULES, simplify_text

ALL_RULES = [
    (language, phrase, replacement)
    for language in LANGUAGES
    for phrase, replacement in sorted(RULES[language].items())
]


def nfc(text):
    return unicodedata.normalize("NFC", text)


def simplified(text, language="en"):
    return simplify_text(text, language)["simplified_text"]


@pytest.mark.parametrize("language", LANGUAGES)
def test_dictionary_sizes(language):
    assert 15 <= len(RULES[language]) <= 20


@pytest.mark.parametrize("language, phrase, replacement", ALL_RULES)
def test_every_dictionary_rule(language, phrase, replacement):
    result = simplify_text(f"({phrase}) 42.", language)
    assert result["simplified_text"] == f"({replacement}) 42."
    assert result["transformations"] == [
        {"original": phrase, "replacement": replacement, "start": 1}
    ]
    assert result["transformation_count"] == 1
    assert result["language"] == language


# English

def test_english_capitalization():
    text = "Prior to Monday, OBTAIN the form. Commence now."
    assert simplified(text) == "Before Monday, GET the form. Begin now."


def test_english_word_boundaries():
    text = "The terminated, indeterminate, obtained and obtainable items."
    assert simplified(text) == text


def test_english_multiple_replacements():
    text = "Applicants are required to submit the requisite documents prior to the deadline."
    result = simplify_text(text, "en")
    assert result["simplified_text"] == (
        "Applicants must submit the required documents before the deadline."
    )
    assert [t["original"] for t in result["transformations"]] == [
        "are required to", "requisite documents", "prior to",
    ]


def test_english_longer_phrase_wins():
    result = simplify_text("The student is required to submit the form.", "en")
    assert result["simplified_text"] == "The student must submit the form."
    assert result["transformations"][0]["original"] == "is required to submit"
    assert simplified("Bring requisite documents and requisite fees.") == (
        "Bring required documents and required fees."
    )


def test_english_preserves_punctuation_numbers_and_names():
    text = "Mr. Rahul Sharma: pay Rs. 1,500 (approximately) per annum prior to 31/03/2025!"
    assert simplified(text) == (
        "Mr. Rahul Sharma: pay Rs. 1,500 (about) per year before 31/03/2025!"
    )


def test_english_phrase_across_line_break():
    assert simplified("Submit it prior\n  to 5 PM.") == "Submit it before 5 PM."


# Hindi

def test_hindi_multiple_replacements():
    text = "अभ्यर्थी अंतिम तिथि से पूर्व आवश्यक दस्तावेज़ प्रस्तुत करें।"
    result = simplify_text(text, "hi")
    assert result["simplified_text"] == nfc(
        "उम्मीदवार आखिरी तारीख से पहले ज़रूरी दस्तावेज़ जमा करें।"
    )
    assert result["transformation_count"] == 5


def test_hindi_longer_phrase_wins():
    result = simplify_text("प्रवेश प्रारंभ करना है। कक्षा प्रारंभ होगी।", "hi")
    assert result["simplified_text"] == "प्रवेश शुरू करना है। कक्षा शुरू होगी।"
    assert [t["original"] for t in result["transformations"]] == ["प्रारंभ करना", "प्रारंभ"]


def test_hindi_matches_both_nukta_encodings():
    precomposed = "आवश्यक दस्तावेज़"  # ज़ as one code point
    decomposed = "आवश्यक दस्तावेज़"  # ज + nukta
    expected = nfc("ज़रूरी दस्तावेज़")
    assert simplified(precomposed, "hi") == expected
    assert simplified(decomposed, "hi") == expected


def test_hindi_word_boundaries_and_numbers():
    # "तिथियाँ" contains "तिथि" but is a different word, so it must not change.
    text = "राम शर्मा: कुल ३ तिथियाँ, शुल्क ₹500 है।"
    assert simplified(text, "hi") == text


def test_hindi_preserves_names_and_numbers():
    text = "सीमा वर्मा, 15 जून तिथि तक सहायता लें।"
    assert simplified(text, "hi") == "सीमा वर्मा, 15 जून तारीख तक मदद लें।"


# Hinglish

def test_hinglish_multiple_replacements_and_capitalization():
    text = "Abhyarthi antim tithi se purv avashyak dastavez prastut karein."
    assert simplified(text, "hinglish") == (
        "Candidate last date se pehle zaroori documents jama karein."
    )


def test_hinglish_longer_phrase_wins():
    result = simplify_text("Admission PRARAMBH KARNA hai, class prarambh hogi.", "hinglish")
    assert result["simplified_text"] == "Admission SHURU KARNA hai, class shuru hogi."


def test_hinglish_word_boundaries():
    text = "Tithiyan aur kese purv wala rule nahi lagega."
    assert simplified(text, "hinglish") == text


# Language isolation and edge cases

def test_rules_do_not_cross_languages():
    english = "Submit prior to Monday."
    hindi = "अंतिम तिथि से पूर्व"
    hinglish = "antim tithi se purv"
    assert simplified(english, "hi") == english
    assert simplified(english, "hinglish") == english
    assert simplified(hindi, "en") == hindi
    assert simplified(hindi, "hinglish") == hindi
    assert simplified(hinglish, "en") == hinglish
    assert simplified(hinglish, "hi") == hinglish


@pytest.mark.parametrize("language", LANGUAGES)
def test_unsupported_phrases_remain_unchanged(language):
    text = "The library opens at 9 AM. पुस्तकालय 9 बजे खुलता hai."
    result = simplify_text(text, language)
    assert result["simplified_text"] == text
    assert result["transformations"] == []
    assert result["transformation_count"] == 0


def test_invalid_language_raises():
    with pytest.raises(ValueError):
        simplify_text("prior to", "fr")


def test_input_string_is_not_modified():
    text = "Obtain assistance prior to Friday."
    result = simplify_text(text, "en")
    assert text == "Obtain assistance prior to Friday."
    assert result["original_text"] == text
