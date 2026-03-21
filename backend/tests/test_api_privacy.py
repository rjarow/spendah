"""Tests for Privacy API endpoints."""

import pytest
from decimal import Decimal


class TestPrivacySettings:
    """Test privacy settings endpoints."""

    def test_get_privacy_settings(self, client):
        """Should return privacy settings."""
        response = client.get("/api/v1/privacy/settings")
        assert response.status_code == 200
        data = response.json()
        assert "obfuscation_enabled" in data
        assert "provider_settings" in data
        assert "stats" in data

    def test_update_obfuscation_enabled(self, client):
        """Should update obfuscation enabled setting."""
        response = client.patch(
            "/api/v1/privacy/settings", json={"obfuscation_enabled": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["obfuscation_enabled"] is True

    def test_update_provider_obfuscation(self, client):
        """Should update provider-specific obfuscation settings."""
        response = client.patch(
            "/api/v1/privacy/settings",
            json={
                "provider_settings": [
                    {"provider": "openrouter", "obfuscation_enabled": False}
                ]
            },
        )
        assert response.status_code == 200

    def test_get_token_stats(self, client):
        """Should return token statistics."""
        response = client.get("/api/v1/privacy/settings")
        assert response.status_code == 200
        data = response.json()
        stats = data["stats"]
        assert "merchants" in stats
        assert "accounts" in stats
        assert "people" in stats
        assert "date_shift_days" in stats


class TestTokenization:
    """Test tokenization endpoints."""

    def test_tokenize_data(self, client):
        """Should tokenize merchant names."""
        response = client.post(
            "/api/v1/privacy/tokenize",
            json={"merchants": ["Whole Foods", "Amazon", "Netflix"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "tokenized" in data
        assert len(data["tokenized"]) == 3

        for item in data["tokenized"]:
            assert "original" in item
            assert "token" in item
            assert item["token"].startswith("MERCHANT_")

    def test_tokenize_empty_list(self, client):
        """Should handle empty merchant list."""
        response = client.post("/api/v1/privacy/tokenize", json={"merchants": []})
        assert response.status_code == 200
        data = response.json()
        assert data["tokenized"] == []

    def test_tokenize_same_merchant_same_token(self, client):
        """Should return same token for same merchant."""
        response1 = client.post(
            "/api/v1/privacy/tokenize", json={"merchants": ["Starbucks"]}
        )
        response2 = client.post(
            "/api/v1/privacy/tokenize", json={"merchants": ["Starbucks"]}
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        token1 = response1.json()["tokenized"][0]["token"]
        token2 = response2.json()["tokenized"][0]["token"]
        assert token1 == token2

    def test_detokenize_data(self, client):
        """Should detokenize tokens back to original values."""
        tokenize_response = client.post(
            "/api/v1/privacy/tokenize", json={"merchants": ["Target"]}
        )
        token = tokenize_response.json()["tokenized"][0]["token"]

        detokenize_response = client.post(
            "/api/v1/privacy/detokenize", json={"tokens": [token]}
        )

        assert detokenize_response.status_code == 200
        data = detokenize_response.json()
        assert "detokenized" in data
        assert len(data["detokenized"]) == 1
        assert data["detokenized"][0]["original"] == "Target"

    def test_detokenize_unknown_token(self, client):
        """Should handle unknown tokens gracefully."""
        response = client.post(
            "/api/v1/privacy/detokenize", json={"tokens": ["UNKNOWN_TOKEN_999"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["detokenized"][0]["original"] is None
