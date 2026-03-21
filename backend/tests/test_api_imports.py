"""Tests for Import API endpoints."""

import pytest
from datetime import date
from decimal import Decimal
import uuid
import io

from app.models.account import Account, AccountType
from app.models.import_log import ImportLog, ImportStatus


class TestImportUpload:
    """Test import upload endpoint."""

    def test_upload_csv_file(self, client, sample_account):
        """Should upload and preview CSV file."""
        csv_content = b"date,amount,description\n2024-01-15,-50.00,Grocery Store\n2024-01-16,-25.00,Gas"

        response = client.post(
            "/api/v1/imports/upload",
            files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
        )

        # The upload endpoint does AI format detection which may fail without AI configured,
        # but should still succeed with basic parsing
        assert response.status_code == 200
        data = response.json()
        assert "import_id" in data
        assert data["filename"] == "test.csv"
        assert data["row_count"] == 2
        assert "headers" in data
        assert "preview_rows" in data

    def test_upload_unsupported_file(self, client):
        """Should reject unsupported file types."""
        response = client.post(
            "/api/v1/imports/upload",
            files={"file": ("test.txt", io.BytesIO(b"content"), "text/plain")},
        )

        assert response.status_code == 400

    def test_upload_missing_file(self, client):
        """Should reject missing file."""
        response = client.post("/api/v1/imports/upload")
        assert response.status_code == 422

    def test_upload_empty_file(self, client):
        """Should handle empty file."""
        response = client.post(
            "/api/v1/imports/upload",
            files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
        )

        assert response.status_code in [400, 500]


class TestImportStatus:
    """Test import status endpoint."""

    def test_get_import_status_not_found(self, client):
        """Should return 404 for non-existent import."""
        response = client.get("/api/v1/imports/nonexistent/status")
        assert response.status_code == 404

    def test_get_import_status(self, client, db_session, sample_account):
        """Should return import status."""
        import_log = ImportLog(
            id=str(uuid.uuid4()),
            filename="test.csv",
            account_id=sample_account.id,
            status=ImportStatus.completed,
            transactions_imported=10,
            transactions_skipped=2,
        )
        db_session.add(import_log)
        db_session.commit()

        response = client.get(f"/api/v1/imports/{import_log.id}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["transactions_imported"] == 10
        assert data["transactions_skipped"] == 2


class TestImportHistory:
    """Test import history endpoint."""

    def test_get_import_history_empty(self, client):
        """Should return empty list when no imports."""
        response = client.get("/api/v1/imports/history")
        assert response.status_code == 200
        data = response.json()
        # API returns a list, not {items, total}
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_import_history(self, client, db_session, sample_account):
        """Should return import history."""
        for i in range(3):
            import_log = ImportLog(
                id=str(uuid.uuid4()),
                filename=f"import_{i}.csv",
                account_id=sample_account.id,
                status=ImportStatus.completed,
                transactions_imported=5,
                transactions_skipped=0,
            )
            db_session.add(import_log)
        db_session.commit()

        response = client.get("/api/v1/imports/history")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
