"""Tests for alerts API endpoints."""

import pytest
import uuid
from datetime import date
from decimal import Decimal

from app.models.alert import Alert, AlertType, Severity
from app.models.transaction import Transaction


class TestAlertsAPI:
    """Test alerts endpoints."""

    def test_list_alerts_empty(self, client):
        """Should return empty list."""
        response = client.get("/api/v1/alerts")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["unread_count"] == 0

    def test_list_alerts_with_data(self, client, db_session):
        """Should return alerts."""
        alert = Alert(
            id=str(uuid.uuid4()),
            type=AlertType.large_purchase,
            severity=Severity.warning,
            title="Test Alert",
            description="Description"
        )
        db_session.add(alert)
        db_session.commit()

        response = client.get("/api/v1/alerts")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Test Alert"

    def test_get_unread_count(self, client, db_session):
        """Should return unread count."""
        alert = Alert(
            id=str(uuid.uuid4()),
            type=AlertType.large_purchase,
            severity=Severity.info,
            title="Unread",
            description="Test",
            is_read=False
        )
        db_session.add(alert)
        db_session.commit()

        response = client.get("/api/v1/alerts/unread-count")
        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_update_alert(self, client, db_session):
        """Should mark alert as read."""
        alert = Alert(
            id=str(uuid.uuid4()),
            type=AlertType.large_purchase,
            severity=Severity.info,
            title="Test",
            description="Test",
            is_read=False
        )
        db_session.add(alert)
        db_session.commit()

        response = client.patch(f"/api/v1/alerts/{alert.id}", json={
            "is_read": True
        })
        assert response.status_code == 200
        assert response.json()["is_read"] is True

    def test_dismiss_alert(self, client, db_session):
        """Should dismiss alert."""
        alert = Alert(
            id=str(uuid.uuid4()),
            type=AlertType.large_purchase,
            severity=Severity.info,
            title="Test",
            description="Test"
        )
        db_session.add(alert)
        db_session.commit()

        response = client.patch(f"/api/v1/alerts/{alert.id}", json={
            "is_dismissed": True
        })
        assert response.status_code == 200

        # Should no longer appear in default list
        response = client.get("/api/v1/alerts")
        assert len(response.json()["items"]) == 0

    def test_mark_all_read(self, client, db_session):
        """Should mark all as read."""
        for i in range(3):
            db_session.add(Alert(
                id=str(uuid.uuid4()),
                type=AlertType.large_purchase,
                severity=Severity.info,
                title=f"Alert {i}",
                description="Test",
                is_read=False
            ))
        db_session.commit()

        response = client.post("/api/v1/alerts/mark-all-read")
        assert response.status_code == 200
        assert response.json()["marked_read"] == 3

    def test_get_alert_settings(self, client, alert_settings):
        """Should return alert settings."""
        response = client.get("/api/v1/alerts/settings")
        assert response.status_code == 200
        data = response.json()
        assert "large_purchase_multiplier" in data
        assert "alerts_enabled" in data

    def test_update_alert_settings(self, client, alert_settings):
        """Should update settings."""
        response = client.patch("/api/v1/alerts/settings", json={
            "large_purchase_multiplier": 5.0
        })
        assert response.status_code == 200
        assert response.json()["large_purchase_multiplier"] == 5.0

    def test_get_upcoming_renewals(self, client, db_session, sample_recurring_group, sample_account):
        """Should return upcoming renewals (Phase 6)."""
        # Add a transaction to recurring group
        txn = Transaction(
            id=str(uuid.uuid4()),
            hash=f"hash-{uuid.uuid4()}",
            date=date(2024, 1, 15),
            amount=Decimal("-15.99"),
            raw_description="NETFLIX",
            account_id=sample_account.id,
            recurring_group_id=sample_recurring_group.id,
            is_recurring=True
        )
        db_session.add(txn)
        db_session.commit()

        # Set next expected date to 7 days in future
        from datetime import timedelta
        sample_recurring_group.next_expected_date = date.today() + timedelta(days=7)
        sample_recurring_group.is_active = True
        db_session.commit()

        response = client.get("/api/v1/alerts/upcoming-renewals?days=30")
        assert response.status_code == 200
        data = response.json()
        assert len(data["renewals"]) == 1
        assert data["renewals"][0]["days_until"] == 7
        assert data["total_upcoming_30_days"] == pytest.approx(15.99, rel=0.01)

    def test_subscription_review(self, client, db_session, sample_recurring_group, sample_account):
        """Should create subscription review alert (Phase 6 - manual trigger only)."""
        # Add transactions to recurring group
        for i in range(3):
            txn = Transaction(
                id=str(uuid.uuid4()),
                hash=f"hash-{uuid.uuid4()}",
                date=date(2024, 1, 15),
                amount=Decimal("-15.99"),
                raw_description="NETFLIX",
                account_id=sample_account.id,
                recurring_group_id=sample_recurring_group.id,
                is_recurring=True
            )
            db_session.add(txn)
        db_session.commit()

        # Set as active
        sample_recurring_group.is_active = True
        sample_recurring_group.next_expected_date = date(2024, 2, 1)
        db_session.commit()

        # Note: This endpoint calls AI, which we're skipping in tests
        # We're just testing the endpoint exists and returns 200
        response = client.post("/api/v1/alerts/subscription-review")
        assert response.status_code == 200
        data = response.json()
        assert "total_monthly_cost" in data
        assert "subscription_count" in data
