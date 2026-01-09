"""Tests for health check endpoint."""


def test_health_check(client):
    """Health endpoint should return ok status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app_name" in data
