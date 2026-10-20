import pytest
from fastapi.testclient import TestClient

from app.main import MAX_TEXT_LENGTH, app

client = TestClient(app)

SAMPLE = (
    "Students with at least 60% marks must submit their resume by 15 November 2026. "
    "The application fee is ₹500."
)


def test_explain_sample():
    response = client.post("/api/explain", json={"text": SAMPLE, "language": "en"})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "language", "original_text", "simplified_text", "transformations",
        "explanation", "facts", "checklist", "sentences",
    }
    assert set(body["facts"]) == {
        "deadlines", "dates", "fees", "eligibility", "required_documents", "action_items",
    }
    assert body["original_text"] == SAMPLE
    assert body["facts"]["deadlines"][0]["iso"] == "2026-11-15"
    assert [i["category"] for i in body["checklist"]] == [
        "eligibility", "required_documents", "action_items", "fees", "deadlines",
    ]


@pytest.mark.parametrize("language, text, first_line", [
    ("hi", "अंतिम तिथि 15 नवंबर 2026 है।", "समय सीमा: 15 नवंबर 2026।"),
    ("hinglish", "Antim tithi 15/11/2026 hai.", "Deadline: 15/11/2026."),
])
def test_explain_hindi_and_hinglish(language, text, first_line):
    body = client.post("/api/explain", json={"text": text, "language": language}).json()
    assert body["language"] == language
    assert body["explanation"][0] == first_line


def test_explain_defaults_to_english():
    assert client.post("/api/explain", json={"text": SAMPLE}).json()["language"] == "en"


@pytest.mark.parametrize("payload", [
    {"text": ""},
    {"text": "  \n\t "},
    {"text": "a" * (MAX_TEXT_LENGTH + 1)},
    {"text": SAMPLE, "language": "fr"},
    {},
])
def test_explain_rejects_invalid_input(payload):
    assert client.post("/api/explain", json=payload).status_code == 422


def test_all_endpoints_still_work():
    assert client.get("/").status_code == 200
    assert client.get("/health").json() == {"status": "healthy"}
    for path in ("/api/process-text", "/api/simplify", "/api/extract-info", "/api/explain"):
        assert client.post(path, json={"text": SAMPLE}).status_code == 200
