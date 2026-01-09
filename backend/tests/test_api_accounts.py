"""Tests for accounts API endpoints."""

import pytest


class TestAccountsAPI:
    """Test accounts CRUD endpoints."""

    def test_list_accounts_empty(self, client):
        """Should return empty list when no accounts."""
        response = client.get("/api/v1/accounts")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_account(self, client):
        """Should create a new account."""
        from app.models.account import AccountType
        response = client.post("/api/v1/accounts", json={
            "name": "My Checking",
            "account_type": AccountType.bank
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My Checking"
        assert data["account_type"] == "bank"
        assert "id" in data

    def test_list_accounts_with_data(self, client, sample_account):
        """Should return accounts when they exist."""
        response = client.get("/api/v1/accounts")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == sample_account.name

    def test_update_account(self, client, sample_account):
        """Should update account name."""
        response = client.patch(f"/api/v1/accounts/{sample_account.id}", json={
            "name": "Updated Name"
        })
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    def test_delete_account(self, client, sample_account):
        """Should soft delete account."""
        response = client.delete(f"/api/v1/accounts/{sample_account.id}")
        assert response.status_code == 200

        # Verify soft deleted
        response = client.get("/api/v1/accounts")
        assert response.json() == []
