from fastapi.testclient import TestClient

from app.main import DEFAULT_CORS_ORIGINS, MAX_PDF_BYTES, app, parse_origins

client = TestClient(app)


def test_parse_origins_ignores_spaces_and_empty_entries():
    assert parse_origins(" https://a.example , https://b.example/,,") == [
        "https://a.example", "https://b.example",
    ]
    assert "http://localhost:5173" in parse_origins(DEFAULT_CORS_ORIGINS)


def test_oversized_upload_is_refused_before_reading_and_keeps_cors_headers():
    response = client.post(
        "/api/process-pdf",
        files={"file": ("big.pdf", b"%PDF-1.7\n" + b"0" * (MAX_PDF_BYTES + 100_000))},
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.status_code == 413
    assert response.json() == {"detail": "The PDF is larger than the 5 MB limit."}
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def preflight(origin):
    return client.options(
        "/api/explain",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )


def test_local_frontend_origin_is_allowed():
    response = preflight("http://localhost:5173")
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_unknown_origin_is_not_allowed():
    response = preflight("http://evil.example")
    assert "access-control-allow-origin" not in response.headers


def test_simple_request_from_frontend_gets_cors_header():
    response = client.post(
        "/api/explain",
        json={"text": "Submit by 15 November 2026."},
        headers={"Origin": "http://127.0.0.1:5173"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
