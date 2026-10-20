import unicodedata

import pytest
from fastapi.testclient import TestClient

from app.main import MAX_TEXT_LENGTH, app

client = TestClient(app)


def test_simplify_english():
    text = "Applicants are required to submit the requisite documents prior to the deadline."
    response = client.post("/api/simplify", json={"text": text, "language": "en"})
    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "en"
    assert body["original_text"] == text
    assert body["simplified_text"] == (
        "Applicants must submit the required documents before the deadline."
    )
    assert body["transformation_count"] == 3
    assert body["transformations"][0] == {
        "original": "are required to", "replacement": "must", "start": 11,
    }


def test_simplify_defaults_to_english():
    response = client.post("/api/simplify", json={"text": "Obtain help."})
    assert response.status_code == 200
    assert response.json()["language"] == "en"
    assert response.json()["simplified_text"] == "Get help."


def test_simplify_hindi():
    text = "अंतिम तिथि से पूर्व आवश्यक दस्तावेज़ प्रस्तुत करें।"
    response = client.post("/api/simplify", json={"text": text, "language": "hi"})
    assert response.status_code == 200
    body = response.json()
    assert body["simplified_text"] == unicodedata.normalize(
        "NFC", "आखिरी तारीख से पहले ज़रूरी दस्तावेज़ जमा करें।"
    )
    assert body["transformation_count"] == 4


def test_simplify_hinglish():
    text = "Antim tithi se purv avashyak dastavez prastut karein."
    response = client.post("/api/simplify", json={"text": text, "language": "hinglish"})
    assert response.status_code == 200
    assert response.json()["simplified_text"] == (
        "Last date se pehle zaroori documents jama karein."
    )


def test_simplify_with_no_matches():
    response = client.post("/api/simplify", json={"text": "The library opens at 9 AM."})
    body = response.json()
    assert body["simplified_text"] == "The library opens at 9 AM."
    assert body["transformations"] == []
    assert body["transformation_count"] == 0


@pytest.mark.parametrize("language", ["fr", "EN", "hindi", "", None, 1])
def test_simplify_rejects_invalid_language(language):
    response = client.post("/api/simplify", json={"text": "prior to", "language": language})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "language"]


def test_simplify_rejects_empty_and_whitespace_text():
    assert client.post("/api/simplify", json={"text": ""}).status_code == 422
    assert client.post("/api/simplify", json={"text": " \n\t ", "language": "hi"}).status_code == 422


def test_simplify_rejects_oversized_text():
    response = client.post(
        "/api/simplify", json={"text": "a" * (MAX_TEXT_LENGTH + 1), "language": "en"}
    )
    assert response.status_code == 422
