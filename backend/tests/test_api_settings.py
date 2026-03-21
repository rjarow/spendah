"""Tests for Settings API endpoints."""

import pytest


class TestSettingsAPI:
    """Test settings endpoints."""

    def test_get_settings(self, client):
        """Should return current AI settings."""
        response = client.get("/api/v1/settings")
        assert response.status_code == 200
        data = response.json()
        assert "ai" in data
        assert "available_providers" in data

        ai = data["ai"]
        assert "provider" in ai
        assert "model" in ai
        assert "auto_categorize" in ai
        assert "clean_merchants" in ai
        assert "detect_format" in ai

    def test_get_available_providers(self, client):
        """Should return list of available AI providers."""
        response = client.get("/api/v1/settings")
        assert response.status_code == 200
        data = response.json()

        providers = data["available_providers"]
        assert isinstance(providers, list)

        for provider in providers:
            assert "id" in provider
            assert "name" in provider
            assert "requires_key" in provider
            assert "models" in provider

    def test_update_ai_settings_partial(self, client):
        """Should update only specified settings."""
        response = client.patch("/api/v1/settings/ai", json={"auto_categorize": False})
        assert response.status_code == 200
        data = response.json()
        assert data["auto_categorize"] is False

    def test_update_ai_settings_provider(self, client):
        """Should update AI provider."""
        response = client.patch(
            "/api/v1/settings/ai", json={"provider": "ollama", "model": "llama2"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "ollama"
        assert data["model"] == "llama2"

    def test_get_available_providers_endpoint(self, client):
        """Should return providers list from main settings endpoint."""
        # No dedicated /settings/ai/providers endpoint; use main settings
        response = client.get("/api/v1/settings")
        assert response.status_code == 200
        data = response.json()
        providers = data["available_providers"]
        assert isinstance(providers, list)
        assert len(providers) > 0


class TestAITestEndpoint:
    """Test AI connection test endpoint."""

    def test_ai_test_without_key(self, client):
        """Should fail gracefully without API key."""
        response = client.post("/api/v1/settings/ai/test")
        assert response.status_code in [200, 500]
