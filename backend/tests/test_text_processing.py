from app.nlp.text_processing import normalize_text, split_sentences, tokenize_text


def test_normalize_collapses_spaces_and_line_breaks():
    text = "  Applicants   must\tsubmit  \n\n\n\n  the documents.  \n"
    assert normalize_text(text) == "Applicants must submit\n\nthe documents."


def test_normalize_keeps_single_line_breaks():
    assert normalize_text("Line one\r\nLine   two") == "Line one\nLine two"


def test_split_single_english_sentence():
    text = "Applicants must submit the required documents."
    assert split_sentences(text) == [text]


def test_split_multiple_sentences():
    text = "Submit the form. Pay the fee! Did you sign it? Yes."
    assert split_sentences(text) == [
        "Submit the form.",
        "Pay the fee!",
        "Did you sign it?",
        "Yes.",
    ]


def test_split_is_conservative_with_abbreviations():
    text = "Contact Dr. Sharma at Rs. 500 per visit, e.g. Monday. Fees are fixed."
    assert split_sentences(text) == [
        "Contact Dr. Sharma at Rs. 500 per visit, e.g. Monday.",
        "Fees are fixed.",
    ]


def test_split_handles_extra_whitespace_and_paragraphs():
    text = "First   sentence\ncontinues here.\n\n\nSecond paragraph"
    assert split_sentences(text) == [
        "First sentence continues here.",
        "Second paragraph",
    ]


def test_split_hindi_sentences():
    text = "नमस्ते दुनिया। यह एक परीक्षण है।"
    assert split_sentences(text) == ["नमस्ते दुनिया।", "यह एक परीक्षण है।"]


def test_tokenize_english():
    assert tokenize_text("Applicants must submit the required documents.") == [
        "Applicants", "must", "submit", "the", "required", "documents", ".",
    ]


def test_tokenize_keeps_contractions_hyphens_and_numbers():
    assert tokenize_text("Don't miss the follow-up: Rs. 1,000.50 due") == [
        "Don't", "miss", "the", "follow-up", ":", "Rs", ".", "1,000.50", "due",
    ]


def test_tokenize_hindi_keeps_words_whole():
    assert tokenize_text("नमस्ते दुनिया। यह परीक्षण है।") == [
        "नमस्ते", "दुनिया", "।", "यह", "परीक्षण", "है", "।",
    ]


def test_tokenize_mixed_hinglish_and_empty():
    assert tokenize_text("Form भरें aur submit करें") == [
        "Form", "भरें", "aur", "submit", "करें",
    ]
    assert tokenize_text("") == []
