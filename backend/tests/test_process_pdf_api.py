import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.main import MAX_TEXT_LENGTH, app
from app.pdf_extraction import MAX_PDF_BYTES, extract_pdf_text

client = TestClient(app)

NOTICE = (
    "Students with at least 60% marks must submit their resume by 15 November 2026.\n"
    "The application fee is Rs. 500."
)


def make_pdf(*pages: str, **save_options) -> bytes:
    """Build a PDF in memory with one page per string (empty string = blank page)."""
    document = pymupdf.open()
    for text in pages:
        page = document.new_page()
        if text:
            page.insert_text((50, 72), text, fontsize=10)
    data = document.tobytes(**save_options)
    document.close()
    return data


def image_only_pdf() -> bytes:
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 20, 20), False)
    pixmap.clear_with(200)
    document = pymupdf.open()
    document.new_page().insert_image(pymupdf.Rect(50, 50, 250, 250), stream=pixmap.tobytes("png"))
    data = document.tobytes()
    document.close()
    return data


def upload(data: bytes, language=None, filename="notice.pdf", content_type="application/pdf"):
    form = {} if language is None else {"language": language}
    return client.post(
        "/api/process-pdf", files={"file": (filename, data, content_type)}, data=form
    )


# Extraction helper

def test_extract_pdf_text_joins_pages():
    text, page_count = extract_pdf_text(make_pdf("First page.", "", "Third page."))
    assert page_count == 3
    assert text == "First page.\n\nThird page."


# Valid PDFs

def test_valid_pdf_is_explained():
    response = upload(make_pdf(NOTICE), "en")
    assert response.status_code == 200
    body = response.json()
    assert body["pdf"] == {"page_count": 1, "character_count": len(NOTICE)}
    assert body["original_text"] == NOTICE
    assert body["facts"]["deadlines"][0]["iso"] == "2026-11-15"
    assert body["facts"]["fees"][0]["value"] == "Rs. 500"
    assert [i["category"] for i in body["checklist"]] == [
        "eligibility", "required_documents", "action_items", "fees", "deadlines",
    ]


def test_pdf_result_matches_explain_endpoint():
    pdf_body = upload(make_pdf(NOTICE), "en").json()
    text_body = client.post("/api/explain", json={"text": NOTICE, "language": "en"}).json()
    del pdf_body["pdf"]
    assert pdf_body == text_body


def test_multi_page_pdf_keeps_pages_as_separate_paragraphs():
    body = upload(make_pdf("Submit by 15 November 2026", "Fee is Rs. 200")).json()
    assert body["pdf"]["page_count"] == 2
    assert [s["original"] for s in body["sentences"]] == [
        "Submit by 15 November 2026", "Fee is Rs. 200",
    ]


def test_content_decides_not_filename_or_content_type():
    response = upload(make_pdf(NOTICE), filename="notice.txt", content_type="text/plain")
    assert response.status_code == 200


# Languages

def test_language_defaults_to_english():
    assert upload(make_pdf(NOTICE)).json()["language"] == "en"
    # An empty form field counts as "not provided".
    assert upload(make_pdf(NOTICE), "").json()["language"] == "en"


def test_hinglish_language_is_used():
    text = "Antim tithi 15/11/2026 hai. Resume upload karein."
    body = upload(make_pdf(text), "hinglish").json()
    assert body["language"] == "hinglish"
    assert body["simplified_text"] == "Last date 15/11/2026 hai. Resume upload karein."
    assert body["explanation"][0] == "Deadline: 15/11/2026."


@pytest.mark.parametrize("language", ["fr", "EN", "hindi"])
def test_unsupported_language_is_rejected(language):
    response = upload(make_pdf(NOTICE), language)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "language"]


# Invalid uploads

def test_non_pdf_upload_is_rejected():
    response = upload(b"Hello, this is plain text.", filename="notes.txt", content_type="text/plain")
    assert response.status_code == 415
    assert "not a PDF" in response.json()["detail"]


def test_fake_pdf_name_and_content_type_are_not_trusted():
    response = upload(b"\x89PNG\r\n\x1a\n not really a pdf")
    assert response.status_code == 415


def test_invalid_pdf_bytes_are_rejected():
    response = upload(b"%PDF-1.7\nthis is not a real PDF body")
    assert response.status_code == 422
    assert "damaged" in response.json()["detail"]


def test_empty_file_is_rejected():
    response = upload(b"")
    assert response.status_code == 422
    assert response.json()["detail"] == "The uploaded file is empty."


def test_missing_file_is_rejected():
    response = client.post("/api/process-pdf", data={"language": "en"})
    assert response.status_code == 422


def test_oversized_upload_is_rejected():
    response = upload(b"%PDF-1.7\n" + b"0" * MAX_PDF_BYTES)
    assert response.status_code == 413
    assert "5 MB" in response.json()["detail"]


def test_blank_pdf_reports_no_readable_text():
    response = upload(make_pdf(""))
    assert response.status_code == 422
    assert "scanned or image-only" in response.json()["detail"]


def test_image_only_pdf_reports_no_readable_text():
    response = upload(image_only_pdf())
    assert response.status_code == 422
    assert "scanned or image-only" in response.json()["detail"]


def test_password_protected_pdf_is_rejected():
    data = make_pdf(
        NOTICE, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="secret", owner_pw="owner"
    )
    response = upload(data)
    assert response.status_code == 422
    assert "password-protected" in response.json()["detail"]


def test_pdf_with_too_much_text_is_rejected():
    line = "This line of the notice is padded to be long enough for the test."
    page_text = "\n".join([line] * 60)
    data = make_pdf(*[page_text] * 6)
    assert len(extract_pdf_text(data)[0]) > MAX_TEXT_LENGTH
    response = upload(data)
    assert response.status_code == 422
    assert "The limit is 20,000" in response.json()["detail"]


# Existing endpoints

def test_existing_text_endpoints_still_work():
    assert client.get("/health").json() == {"status": "healthy"}
    for path in ("/api/process-text", "/api/simplify", "/api/extract-info", "/api/explain"):
        assert client.post(path, json={"text": NOTICE}).status_code == 200
