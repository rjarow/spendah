"""Tests for transactions API endpoints."""

import pytest


class TestTransactionsAPI:
    """Test transactions endpoints."""

    def test_list_transactions_empty(self, client):
        """Should return empty paginated list."""
        response = client.get("/api/v1/transactions")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_transactions_with_data(self, client, sample_transaction):
        """Should return transactions."""
        response = client.get("/api/v1/transactions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1

    def test_get_transaction(self, client, sample_transaction):
        """Should return single transaction."""
        response = client.get(f"/api/v1/transactions/{sample_transaction.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_transaction.id

    def test_update_transaction_category(self, client, sample_transaction, sample_category):
        """Should update transaction category."""
        response = client.patch(
            f"/api/v1/transactions/{sample_transaction.id}",
            json={"category_id": sample_category.id}
        )
        assert response.status_code == 200
        assert response.json()["category_id"] == sample_category.id

    def test_search_transactions(self, client, sample_transaction):
        """Should filter by search term."""
        response = client.get("/api/v1/transactions", params={"search": "Whole"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1

        response = client.get("/api/v1/transactions", params={"search": "xyz"})
        data = response.json()
        assert len(data["items"]) == 0
