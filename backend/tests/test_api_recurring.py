"""Tests for Recurring API endpoints."""

import pytest
from datetime import date, timedelta
from decimal import Decimal
import uuid

from app.models.recurring import RecurringGroup, Frequency
from app.models.transaction import Transaction


class TestRecurringList:
    """Test recurring groups list endpoint."""

    def test_list_recurring_empty(self, client):
        """Should return empty list when no recurring groups."""
        response = client.get("/api/v1/recurring")
        assert response.status_code == 200
        data = response.json()
        # API returns a list, not {items, total}
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_recurring_with_groups(
        self, client, db_session, sample_recurring_group
    ):
        """Should return list of recurring groups."""
        response = client.get("/api/v1/recurring")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == sample_recurring_group.name

    def test_list_recurring_only_active(self, client, db_session, sample_category):
        """Should only return active recurring groups by default."""
        active_group = RecurringGroup(
            id=str(uuid.uuid4()),
            name="Active Sub",
            merchant_pattern="Active",
            expected_amount=Decimal("10.00"),
            frequency=Frequency.monthly,
            category_id=sample_category.id,
            is_active=True,
        )
        inactive_group = RecurringGroup(
            id=str(uuid.uuid4()),
            name="Inactive Sub",
            merchant_pattern="Inactive",
            expected_amount=Decimal("20.00"),
            frequency=Frequency.monthly,
            category_id=sample_category.id,
            is_active=False,
        )
        db_session.add_all([active_group, inactive_group])
        db_session.commit()

        response = client.get("/api/v1/recurring")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Active Sub"

    def test_list_recurring_include_inactive(self, client, db_session, sample_category):
        """Should include inactive when requested."""
        active_group = RecurringGroup(
            id=str(uuid.uuid4()),
            name="Active",
            merchant_pattern="Active",
            expected_amount=Decimal("10.00"),
            frequency=Frequency.monthly,
            category_id=sample_category.id,
            is_active=True,
        )
        inactive_group = RecurringGroup(
            id=str(uuid.uuid4()),
            name="Inactive",
            merchant_pattern="Inactive",
            expected_amount=Decimal("20.00"),
            frequency=Frequency.monthly,
            category_id=sample_category.id,
            is_active=False,
        )
        db_session.add_all([active_group, inactive_group])
        db_session.commit()

        response = client.get("/api/v1/recurring?include_inactive=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestRecurringCRUD:
    """Test recurring groups CRUD operations."""

    def test_create_recurring_group(self, client, sample_category):
        """Should create a new recurring group."""
        response = client.post(
            "/api/v1/recurring",
            json={
                "name": "Spotify",
                "merchant_pattern": "SPOTIFY",
                "expected_amount": "9.99",
                "frequency": "monthly",
                "category_id": sample_category.id,
            },
        )
        # API returns 200 (no explicit status_code=201 on endpoint)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Spotify"
        assert data["merchant_pattern"] == "SPOTIFY"
        assert data["frequency"] == "monthly"

    def test_get_recurring_group(self, client, sample_recurring_group):
        """Should get a single recurring group."""
        response = client.get(f"/api/v1/recurring/{sample_recurring_group.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_recurring_group.id
        assert data["name"] == sample_recurring_group.name

    def test_get_recurring_group_not_found(self, client):
        """Should return 404 for non-existent group."""
        response = client.get("/api/v1/recurring/nonexistent")
        assert response.status_code == 404

    def test_update_recurring_group(self, client, sample_recurring_group):
        """Should update a recurring group."""
        response = client.patch(
            f"/api/v1/recurring/{sample_recurring_group.id}",
            json={"expected_amount": "20.00"},
        )
        assert response.status_code == 200
        data = response.json()
        assert float(data["expected_amount"]) == 20.0

    def test_delete_recurring_group(self, client, db_session, sample_recurring_group):
        """Should delete a recurring group."""
        response = client.delete(f"/api/v1/recurring/{sample_recurring_group.id}")
        assert response.status_code == 200

        deleted = (
            db_session.query(RecurringGroup)
            .filter_by(id=sample_recurring_group.id)
            .first()
        )
        assert deleted is None


class TestRecurringDetection:
    """Test recurring pattern detection."""

    def test_detect_recurring_patterns_empty(self, client):
        """Should return empty when no transactions."""
        response = client.post("/api/v1/recurring/detect")
        assert response.status_code == 200
        data = response.json()
        assert data["detected"] == []
        assert data["total_found"] == 0
