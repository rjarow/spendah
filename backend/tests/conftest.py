"""Shared test fixtures."""

import pytest
from sqlalchemy import create_engine, inspect, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from datetime import date
from decimal import Decimal
import uuid

from app.database import Base, get_db as database_get_db
from app.dependencies import get_db as dependencies_get_db
from app.main import app
from app.models.account import Account, AccountType
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.recurring import RecurringGroup, Frequency
from app.models.alert import Alert, AlertType, Severity, AlertSettings


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test using in-memory SQLite."""
    # Use StaticPool to ensure all connections use the same in-memory database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    # Override both get_db functions (some routes use app.database, others use app.dependencies)
    app.dependency_overrides[database_get_db] = override_get_db
    app.dependency_overrides[dependencies_get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_account(db_session):
    """Create a sample account."""
    account = Account(id=str(uuid.uuid4()), name="Test Checking")
    account.account_type = AccountType.bank
    account.is_active = True

    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def sample_category(db_session):
    """Create a sample category."""
    category = Category(
        id=str(uuid.uuid4()),
        name="Groceries",
        color="#22c55e",
        icon="shopping-cart",
        is_system=True
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


@pytest.fixture
def sample_transaction(db_session, sample_account, sample_category):
    """Create a sample transaction."""
    txn = Transaction(
        id=str(uuid.uuid4()),
        hash="abc123",
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        raw_description="WHOLE FOODS #1234",
        clean_merchant="Whole Foods",
        category_id=sample_category.id,
        account_id=sample_account.id,
        is_recurring=False,
        ai_categorized=True
    )
    db_session.add(txn)
    db_session.commit()
    db_session.refresh(txn)
    return txn


@pytest.fixture
def sample_recurring_group(db_session, sample_category):
    """Create a sample recurring group."""
    group = RecurringGroup(
        id=str(uuid.uuid4()),
        name="Netflix",
        merchant_pattern="Netflix",
        expected_amount=Decimal("15.99"),
        amount_variance=Decimal("15.0"),
        frequency=Frequency.monthly,
        category_id=sample_category.id,
        is_active=True,
        last_seen_date=date(2024, 1, 1),
        next_expected_date=date(2024, 2, 1)
    )
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)
    return group


@pytest.fixture
def alert_settings(db_session):
    """Create default alert settings."""
    settings = AlertSettings(
        id=str(uuid.uuid4()),  # String UUID as expected by model
        large_purchase_multiplier=Decimal("3.0"),
        unusual_merchant_threshold=Decimal("200.0"),
        alerts_enabled=True
    )
    db_session.add(settings)
    db_session.commit()
    db_session.refresh(settings)
    return settings
