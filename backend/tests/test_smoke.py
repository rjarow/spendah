"""
End-to-end smoke test for Spendah.

This test validates the core import workflow:
1. Seeds the database with categories
2. Creates an account
3. Imports a small CSV (simulated)
4. Verifies transactions were created with correct amounts
5. Checks budget alert flow
6. Verifies dashboard summary returns correct totals
"""

import pytest
import uuid
import asyncio
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.dependencies import get_db
from app.models.account import Account, AccountType
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.budget import Budget, BudgetPeriod
from app.models.alert import AlertSettings
from app.seed import seed_categories
from app.services.import_service import save_upload, get_preview, process_import
from app.services.deduplication_service import generate_transaction_hash
from app.schemas.import_file import ImportConfirmRequest, ColumnMapping


@pytest.fixture(scope="function")
def smoke_db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool
    from sqlalchemy.orm import sessionmaker
    from app.database import Base

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture(scope="function")
def smoke_client(smoke_db_session):
    def override_get_db():
        try:
            yield smoke_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _run_async(coro):
    """Helper to run async functions in sync tests."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestSmokeE2E:
    def test_full_import_workflow(
        self, smoke_db_session: Session, smoke_client: TestClient
    ):
        account = Account(
            id=str(uuid.uuid4()),
            name="Test Checking",
            account_type=AccountType.checking,
            is_active=True,
            current_balance=Decimal("1000.00"),
        )
        smoke_db_session.add(account)
        smoke_db_session.commit()

        parent = Category(
            id=str(uuid.uuid4()),
            name="Food",
            color="#22c55e",
            icon="utensils",
            is_system=True,
        )
        child = Category(
            id=str(uuid.uuid4()),
            name="Groceries",
            parent_id=parent.id,
            color="#22c55e",
            icon="shopping-cart",
            is_system=True,
        )
        smoke_db_session.add_all([parent, child])
        smoke_db_session.commit()

        csv_content = b"""date,amount,description
2024-01-15,-50.00,WHOLE FOODS #1234
2024-01-16,-25.50,TRADER JOES #567
2024-01-17,1500.00,PAYROLL DEPOSIT
2024-01-18,-12.99,NETFLIX.COM
"""
        file_path, import_id = save_upload(csv_content, "test_transactions.csv")

        try:
            preview = get_preview(
                smoke_db_session, file_path, import_id, "test_transactions.csv"
            )

            assert preview.row_count == 4
            assert len(preview.headers) == 3
            assert "date" in [h.lower() for h in preview.headers]

            request = ImportConfirmRequest(
                account_id=account.id,
                column_mapping=ColumnMapping(
                    date_col=0,
                    amount_col=1,
                    description_col=2,
                ),
                date_format="%Y-%m-%d",
            )

            # process_import is async
            result = _run_async(
                process_import(smoke_db_session, import_id, request, use_ai=False)
            )

            assert result.status == "completed"
            assert result.transactions_imported == 4
            assert result.transactions_skipped == 0

            transactions = (
                smoke_db_session.query(Transaction)
                .filter(Transaction.account_id == account.id)
                .all()
            )

            assert len(transactions) == 4

            amounts = sorted([float(t.amount) for t in transactions])
            assert amounts == [-50.0, -25.5, -12.99, 1500.0]

            response = smoke_client.get("/api/v1/dashboard/summary?month=2024-01")
            assert response.status_code == 200
            data = response.json()

            assert data["total_income"] == 1500.0
            assert data["total_expenses"] == 88.49
            assert data["net"] == pytest.approx(1411.51, rel=0.01)

        finally:
            import os

            if file_path.exists():
                os.remove(file_path)

    def test_empty_state_no_crash(self, smoke_client: TestClient):
        response = smoke_client.get("/api/v1/accounts")
        assert response.status_code == 200
        assert response.json()["total"] == 0

        response = smoke_client.get("/api/v1/transactions")
        assert response.status_code == 200
        assert response.json()["total"] == 0

        response = smoke_client.get("/api/v1/budgets")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

        response = smoke_client.get("/api/v1/dashboard/summary")
        assert response.status_code == 200

    def test_duplicate_detection(self, smoke_db_session: Session):
        account = Account(
            id=str(uuid.uuid4()),
            name="Test Checking",
            account_type=AccountType.checking,
            is_active=True,
        )
        smoke_db_session.add(account)
        smoke_db_session.commit()

        # Generate the same hash the import service will generate
        dup_hash = generate_transaction_hash(
            date(2024, 1, 15), Decimal("-50.00"), "WHOLE FOODS", account.id
        )
        txn1 = Transaction(
            id=str(uuid.uuid4()),
            hash=dup_hash,
            date=date(2024, 1, 15),
            amount=Decimal("-50.00"),
            raw_description="WHOLE FOODS",
            account_id=account.id,
            ai_categorized=False,
        )
        smoke_db_session.add(txn1)
        smoke_db_session.commit()

        csv_content = b"""date,amount,description
2024-01-15,-50.00,WHOLE FOODS
2024-01-16,-25.00,OTHER STORE
"""
        file_path, import_id = save_upload(csv_content, "test_dup.csv")

        try:
            # Need to populate pending import via get_preview
            get_preview(smoke_db_session, file_path, import_id, "test_dup.csv")

            request = ImportConfirmRequest(
                account_id=account.id,
                column_mapping=ColumnMapping(
                    date_col=0,
                    amount_col=1,
                    description_col=2,
                ),
                date_format="%Y-%m-%d",
            )

            # process_import is async
            result = _run_async(
                process_import(smoke_db_session, import_id, request, use_ai=False)
            )

            assert result.transactions_imported == 1
            assert result.transactions_skipped == 1

            total = (
                smoke_db_session.query(Transaction)
                .filter(Transaction.account_id == account.id)
                .count()
            )
            assert total == 2

        finally:
            import os

            if file_path.exists():
                os.remove(file_path)

    def test_budget_alert_flow(
        self, smoke_db_session: Session, smoke_client: TestClient
    ):
        from app.services.budget_alerts import check_all_budget_alerts

        account = Account(
            id=str(uuid.uuid4()),
            name="Test Checking",
            account_type=AccountType.checking,
            is_active=True,
        )
        category = Category(
            id=str(uuid.uuid4()),
            name="Groceries",
            color="#22c55e",
            is_system=True,
        )
        smoke_db_session.add_all([account, category])
        smoke_db_session.commit()

        budget = Budget(
            id=str(uuid.uuid4()),
            category_id=category.id,
            amount=Decimal("100.00"),
            period=BudgetPeriod.monthly,
            start_date=date.today().replace(day=1),
            is_active=True,
        )
        smoke_db_session.add(budget)

        alert_settings = AlertSettings(
            id=str(uuid.uuid4()),
            large_purchase_multiplier=Decimal("3.0"),
            unusual_merchant_threshold=Decimal("200.0"),
            alerts_enabled=True,
        )
        smoke_db_session.add(alert_settings)
        smoke_db_session.commit()

        for i, amount in enumerate([-30.00, -40.00, -50.00]):
            txn = Transaction(
                id=str(uuid.uuid4()),
                hash=f"hash_{i}",
                date=date.today(),
                amount=Decimal(str(amount)),
                raw_description=f"STORE {i}",
                account_id=account.id,
                category_id=category.id,
                ai_categorized=False,
            )
            smoke_db_session.add(txn)
        smoke_db_session.commit()

        check_all_budget_alerts(smoke_db_session)

        response = smoke_client.get("/api/v1/alerts")
        assert response.status_code == 200
