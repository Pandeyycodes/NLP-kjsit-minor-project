from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


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
