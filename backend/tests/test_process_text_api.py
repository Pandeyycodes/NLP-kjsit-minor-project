from fastapi.testclient import TestClient

from app.main import MAX_TEXT_LENGTH, app

client = TestClient(app)


def test_process_english_text():
    response = client.post(
        "/api/process-text",
        json={"text": "Applicants must submit the required documents."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["normalized_text"] == "Applicants must submit the required documents."
    assert body["sentences"] == ["Applicants must submit the required documents."]
    assert body["sentence_count"] == 1
    assert body["tokens"][-1] == "."
    assert body["token_count"] == 7


def test_process_multiple_sentences_with_extra_whitespace():
    response = client.post(
        "/api/process-text",
        json={"text": "  Fill the form.   Pay the fee.\n\n\nWait  for approval. "},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["normalized_text"] == "Fill the form. Pay the fee.\n\nWait for approval."
    assert body["sentences"] == ["Fill the form.", "Pay the fee.", "Wait for approval."]


def test_process_hindi_text():
    response = client.post("/api/process-text", json={"text": "नमस्ते दुनिया। यह परीक्षण है।"})
    assert response.status_code == 200
    body = response.json()
    assert body["sentences"] == ["नमस्ते दुनिया।", "यह परीक्षण है।"]
    assert "नमस्ते" in body["tokens"]


def test_rejects_empty_text():
    assert client.post("/api/process-text", json={"text": ""}).status_code == 422


def test_rejects_whitespace_only_text():
    assert client.post("/api/process-text", json={"text": "  \n\t "}).status_code == 422


def test_rejects_missing_text_field():
    assert client.post("/api/process-text", json={}).status_code == 422


def test_accepts_text_at_length_limit():
    response = client.post("/api/process-text", json={"text": "a" * MAX_TEXT_LENGTH})
    assert response.status_code == 200


def test_rejects_text_over_length_limit():
    response = client.post("/api/process-text", json={"text": "a" * (MAX_TEXT_LENGTH + 1)})
    assert response.status_code == 422
