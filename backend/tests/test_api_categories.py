"""Tests for categories API endpoints."""

import pytest


class TestCategoriesAPI:
    """Test categories CRUD endpoints."""

    def test_list_categories(self, client, sample_category):
        """Should return categories."""
        response = client.get("/api/v1/categories")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_create_category(self, client):
        """Should create a new category."""
        response = client.post("/api/v1/categories", json={
            "name": "New Category",
            "color": "#ff0000",
            "icon": "star"
        })
        assert response.status_code in [200, 201]  # Accept both
        data = response.json()
        assert data["name"] == "New Category"
        assert data["color"] == "#ff0000"

    def test_create_subcategory(self, client, sample_category):
        """Should create a subcategory."""
        response = client.post("/api/v1/categories", json={
            "name": "Subcategory",
            "parent_id": sample_category.id,
            "color": "#00ff00"
        })
        assert response.status_code in [200, 201]  # Accept both
        data = response.json()
        assert data["parent_id"] == sample_category.id
