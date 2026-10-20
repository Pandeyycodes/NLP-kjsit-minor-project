import pytest
from fastapi.testclient import TestClient

from app.main import MAX_TEXT_LENGTH, app

client = TestClient(app)

SAMPLE = (
    "Students with at least 60% marks must submit their resume by 15 November 2026. "
    "The application fee is ₹500."
)


def test_extract_info_sample():
    response = client.post("/api/extract-info", json={"text": SAMPLE, "language": "en"})
    assert response.status_code == 200
    body = response.json()
    first, second = (
        "Students with at least 60% marks must submit their resume by 15 November 2026.",
        "The application fee is ₹500.",
    )
    assert body["language"] == "en"
    assert body["deadlines"] == [{
        "value": "15 November 2026", "iso": "2026-11-15", "note": None,
        "rule": "deadline_cue", "cue": "by", "source": first,
    }]
    assert body["dates"][0]["rule"] == "date_day_month_year"
    assert body["fees"] == [{
        "value": "₹500", "amount": 500, "amount_max": None, "currency": "INR",
        "rule": "currency_before_amount", "source": second,
    }]
    assert body["eligibility"] == [
        {"value": "at least 60% marks", "rule": "eligibility_phrase", "source": first}
    ]
    assert body["required_documents"] == [
        {"value": "resume", "rule": "document_name", "source": first}
    ]
    assert body["action_items"] == [
        {"value": "submit", "rule": "action_phrase", "source": first}
    ]


def test_extract_info_defaults_to_english():
    response = client.post("/api/extract-info", json={"text": SAMPLE})
    assert response.status_code == 200
    assert response.json()["language"] == "en"


def test_extract_info_hindi_and_hinglish():
    hindi = client.post(
        "/api/extract-info", json={"text": "अंतिम तिथि 15 नवंबर 2026 है।", "language": "hi"}
    ).json()
    assert hindi["deadlines"][0]["iso"] == "2026-11-15"
    hinglish = client.post(
        "/api/extract-info", json={"text": "Resume upload karein.", "language": "hinglish"}
    ).json()
    assert [a["value"] for a in hinglish["action_items"]] == ["upload karein"]


def test_extract_info_no_findings():
    body = client.post("/api/extract-info", json={"text": "The library opens at 9 AM."}).json()
    for key in ["deadlines", "dates", "fees", "eligibility", "required_documents", "action_items"]:
        assert body[key] == []


@pytest.mark.parametrize("payload", [
    {"text": ""},
    {"text": "  \n\t "},
    {"text": "a" * (MAX_TEXT_LENGTH + 1)},
    {"text": SAMPLE, "language": "fr"},
    {},
])
def test_extract_info_rejects_invalid_input(payload):
    assert client.post("/api/extract-info", json=payload).status_code == 422


def test_existing_endpoints_still_work():
    assert client.get("/").status_code == 200
    assert client.get("/health").json() == {"status": "healthy"}
    assert client.post("/api/process-text", json={"text": SAMPLE}).status_code == 200
    assert client.post("/api/simplify", json={"text": SAMPLE, "language": "en"}).status_code == 200
