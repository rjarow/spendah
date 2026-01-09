# Spendah - Testing Foundation

## Progress Tracker

Update this as you complete each step:

- [ ] Step 1: Backend - Install Test Dependencies
- [ ] Step 2: Backend - Create Test Configuration
- [ ] Step 3: Backend - Test Fixtures (conftest.py)
- [ ] Step 4: Backend - Deduplication Service Tests
- [ ] Step 5: Backend - Recurring Service Tests (non-AI)
- [ ] Step 6: Backend - Alerts Service Tests (non-AI)
- [ ] Step 7: Backend - API Endpoint Tests
- [ ] Step 8: Verify All Tests Pass

## Files to Create/Modify

**CREATE:**
- `backend/tests/conftest.py`
- `backend/tests/test_deduplication.py`
- `backend/tests/test_recurring_service.py`
- `backend/tests/test_alerts_service.py`
- `backend/tests/test_api_health.py`
- `backend/tests/test_api_accounts.py`
- `backend/tests/test_api_categories.py`
- `backend/tests/test_api_transactions.py`
- `backend/tests/test_api_alerts.py`

**MODIFY:**
- `backend/requirements.txt` - Add pytest dependencies

---

## Philosophy

This establishes a **practical testing foundation**:
- Focus on deterministic, critical logic (hashing, date math, thresholds)
- Test API contracts (endpoints return expected shapes)
- Skip AI/LLM tests (too brittle, require mocking complexity)
- Keep tests fast and maintainable

Future phases will include tests for new features following this pattern.

---

## Deliverables

### Step 1: Backend - Install Test Dependencies

Add to `backend/requirements.txt`:

```
# Testing
pytest>=7.0.0
pytest-asyncio>=0.21.0
httpx>=0.24.0
```

Rebuild:
```bash
docker compose build api
```

---

### Step 2: Backend - Create Test Configuration

Create `backend/pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
asyncio_mode = auto
filterwarnings =
    ignore::DeprecationWarning
```

---

### Step 3: Backend - Test Fixtures

Create `backend/tests/conftest.py`:

```python
"""Shared test fixtures."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from datetime import date
from decimal import Decimal
import uuid

from app.database import Base, get_db
from app.main import app
from app.models.account import Account, AccountType
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.recurring import RecurringGroup, Frequency
from app.models.alert import Alert, AlertType, Severity, AlertSettings


# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_account(db_session):
    """Create a sample account."""
    account = Account(
        id=str(uuid.uuid4()),
        name="Test Checking",
        account_type=AccountType.bank,
        is_active=True
    )
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
        id=str(uuid.uuid4()),
        large_purchase_multiplier=Decimal("3.0"),
        unusual_merchant_threshold=Decimal("200.0"),
        alerts_enabled=True
    )
    db_session.add(settings)
    db_session.commit()
    db_session.refresh(settings)
    return settings
```

**Verify:**
```bash
docker compose exec api python -c "import pytest; print('pytest available')"
```

---

### Step 4: Backend - Deduplication Service Tests

Create `backend/tests/test_deduplication.py`:

```python
"""Tests for transaction deduplication logic."""

import pytest
from datetime import date
from decimal import Decimal

from app.services.import_service import generate_transaction_hash, is_duplicate
from app.models.transaction import Transaction


class TestTransactionHash:
    """Test hash generation for deduplication."""
    
    def test_same_inputs_same_hash(self):
        """Identical inputs should produce identical hashes."""
        hash1 = generate_transaction_hash(
            date(2024, 1, 15),
            Decimal("-50.00"),
            "AMAZON PURCHASE",
            "account-123"
        )
        hash2 = generate_transaction_hash(
            date(2024, 1, 15),
            Decimal("-50.00"),
            "AMAZON PURCHASE",
            "account-123"
        )
        assert hash1 == hash2
    
    def test_different_date_different_hash(self):
        """Different dates should produce different hashes."""
        hash1 = generate_transaction_hash(
            date(2024, 1, 15),
            Decimal("-50.00"),
            "AMAZON",
            "account-123"
        )
        hash2 = generate_transaction_hash(
            date(2024, 1, 16),
            Decimal("-50.00"),
            "AMAZON",
            "account-123"
        )
        assert hash1 != hash2
    
    def test_different_amount_different_hash(self):
        """Different amounts should produce different hashes."""
        hash1 = generate_transaction_hash(
            date(2024, 1, 15),
            Decimal("-50.00"),
            "AMAZON",
            "account-123"
        )
        hash2 = generate_transaction_hash(
            date(2024, 1, 15),
            Decimal("-51.00"),
            "AMAZON",
            "account-123"
        )
        assert hash1 != hash2
    
    def test_different_description_different_hash(self):
        """Different descriptions should produce different hashes."""
        hash1 = generate_transaction_hash(
            date(2024, 1, 15),
            Decimal("-50.00"),
            "AMAZON PURCHASE 1",
            "account-123"
        )
        hash2 = generate_transaction_hash(
            date(2024, 1, 15),
            Decimal("-50.00"),
            "AMAZON PURCHASE 2",
            "account-123"
        )
        assert hash1 != hash2
    
    def test_different_account_different_hash(self):
        """Same transaction on different accounts should have different hashes."""
        hash1 = generate_transaction_hash(
            date(2024, 1, 15),
            Decimal("-50.00"),
            "AMAZON",
            "account-123"
        )
        hash2 = generate_transaction_hash(
            date(2024, 1, 15),
            Decimal("-50.00"),
            "AMAZON",
            "account-456"
        )
        assert hash1 != hash2
    
    def test_description_case_insensitive(self):
        """Description comparison should be case-insensitive."""
        hash1 = generate_transaction_hash(
            date(2024, 1, 15),
            Decimal("-50.00"),
            "AMAZON PURCHASE",
            "account-123"
        )
        hash2 = generate_transaction_hash(
            date(2024, 1, 15),
            Decimal("-50.00"),
            "amazon purchase",
            "account-123"
        )
        assert hash1 == hash2
    
    def test_description_whitespace_trimmed(self):
        """Leading/trailing whitespace should be trimmed."""
        hash1 = generate_transaction_hash(
            date(2024, 1, 15),
            Decimal("-50.00"),
            "AMAZON",
            "account-123"
        )
        hash2 = generate_transaction_hash(
            date(2024, 1, 15),
            Decimal("-50.00"),
            "  AMAZON  ",
            "account-123"
        )
        assert hash1 == hash2
    
    def test_hash_is_sha256(self):
        """Hash should be 64 character hex string (SHA256)."""
        hash_val = generate_transaction_hash(
            date(2024, 1, 15),
            Decimal("-50.00"),
            "AMAZON",
            "account-123"
        )
        assert len(hash_val) == 64
        assert all(c in '0123456789abcdef' for c in hash_val)


class TestIsDuplicate:
    """Test duplicate detection in database."""
    
    def test_no_duplicate_empty_db(self, db_session):
        """No duplicate when database is empty."""
        assert is_duplicate(db_session, "somehash123") is False
    
    def test_finds_duplicate(self, db_session, sample_transaction):
        """Should find existing transaction by hash."""
        assert is_duplicate(db_session, sample_transaction.hash) is True
    
    def test_no_false_positive(self, db_session, sample_transaction):
        """Should not match different hashes."""
        assert is_duplicate(db_session, "differenthash456") is False
```

**Verify:**
```bash
docker compose exec api pytest tests/test_deduplication.py -v
```

---

### Step 5: Backend - Recurring Service Tests (non-AI)

Create `backend/tests/test_recurring_service.py`:

```python
"""Tests for recurring service date calculations and group management."""

import pytest
from datetime import date
from decimal import Decimal

from app.services.recurring_service import (
    calculate_next_expected,
    get_group_transaction_count,
)
from app.models.recurring import Frequency
from app.models.transaction import Transaction


class TestCalculateNextExpected:
    """Test next expected date calculations."""
    
    def test_weekly(self):
        """Weekly should add 7 days."""
        result = calculate_next_expected(date(2024, 1, 15), Frequency.weekly)
        assert result == date(2024, 1, 22)
    
    def test_biweekly(self):
        """Biweekly should add 14 days."""
        result = calculate_next_expected(date(2024, 1, 15), Frequency.biweekly)
        assert result == date(2024, 1, 29)
    
    def test_monthly_normal(self):
        """Monthly should add one month."""
        result = calculate_next_expected(date(2024, 1, 15), Frequency.monthly)
        assert result == date(2024, 2, 15)
    
    def test_monthly_year_rollover(self):
        """Monthly in December should roll to January."""
        result = calculate_next_expected(date(2024, 12, 15), Frequency.monthly)
        assert result == date(2025, 1, 15)
    
    def test_monthly_end_of_month(self):
        """Monthly on 31st should handle shorter months."""
        result = calculate_next_expected(date(2024, 1, 31), Frequency.monthly)
        # February doesn't have 31 days, should fall back to 28
        assert result == date(2024, 2, 28)
    
    def test_quarterly(self):
        """Quarterly should add 3 months."""
        result = calculate_next_expected(date(2024, 1, 15), Frequency.quarterly)
        assert result == date(2024, 4, 15)
    
    def test_quarterly_year_rollover(self):
        """Quarterly in November should roll to next year."""
        result = calculate_next_expected(date(2024, 11, 15), Frequency.quarterly)
        assert result == date(2025, 2, 15)
    
    def test_yearly(self):
        """Yearly should add one year."""
        result = calculate_next_expected(date(2024, 1, 15), Frequency.yearly)
        assert result == date(2025, 1, 15)
    
    def test_yearly_leap_day(self):
        """Yearly on Feb 29 should handle non-leap years."""
        result = calculate_next_expected(date(2024, 2, 29), Frequency.yearly)
        # 2025 is not a leap year
        assert result == date(2025, 2, 28) or result == date(2025, 3, 1)


class TestGroupTransactionCount:
    """Test transaction counting for recurring groups."""
    
    def test_empty_group(self, db_session, sample_recurring_group):
        """Empty group should have count of 0."""
        count = get_group_transaction_count(db_session, sample_recurring_group.id)
        assert count == 0
    
    def test_with_transactions(self, db_session, sample_recurring_group, sample_account):
        """Should count transactions in group."""
        # Add transactions to the recurring group
        for i in range(3):
            txn = Transaction(
                id=f"txn-{i}",
                hash=f"hash-{i}",
                date=date(2024, 1, i + 1),
                amount=Decimal("-15.99"),
                raw_description="NETFLIX",
                account_id=sample_account.id,
                recurring_group_id=sample_recurring_group.id,
                is_recurring=True
            )
            db_session.add(txn)
        db_session.commit()
        
        count = get_group_transaction_count(db_session, sample_recurring_group.id)
        assert count == 3
    
    def test_only_counts_group_transactions(self, db_session, sample_recurring_group, sample_transaction):
        """Should not count transactions from other groups."""
        # sample_transaction is not in sample_recurring_group
        count = get_group_transaction_count(db_session, sample_recurring_group.id)
        assert count == 0
```

**Verify:**
```bash
docker compose exec api pytest tests/test_recurring_service.py -v
```

---

### Step 6: Backend - Alerts Service Tests (non-AI)

Create `backend/tests/test_alerts_service.py`:

```python
"""Tests for alerts service threshold logic."""

import pytest
from datetime import date, datetime
from decimal import Decimal
import uuid

from app.services.alerts_service import (
    get_or_create_settings,
    get_category_average,
    is_first_time_merchant,
    check_price_increase,
    get_alerts,
    get_unread_count,
    mark_all_read,
)
from app.models.transaction import Transaction
from app.models.alert import Alert, AlertType, Severity


class TestAlertSettings:
    """Test alert settings management."""
    
    def test_creates_default_settings(self, db_session):
        """Should create default settings if none exist."""
        settings = get_or_create_settings(db_session)
        assert settings is not None
        assert float(settings.large_purchase_multiplier) == 3.0
        assert float(settings.unusual_merchant_threshold) == 200.0
        assert settings.alerts_enabled is True
    
    def test_returns_existing_settings(self, db_session, alert_settings):
        """Should return existing settings, not create new."""
        settings = get_or_create_settings(db_session)
        assert settings.id == alert_settings.id


class TestCategoryAverage:
    """Test category spending average calculation."""
    
    def test_no_transactions(self, db_session, sample_category):
        """Average should be 0 with no transactions."""
        avg = get_category_average(db_session, sample_category.id)
        assert avg == 0.0
    
    def test_calculates_average(self, db_session, sample_category, sample_account):
        """Should calculate average of expenses."""
        # Add some transactions
        amounts = [Decimal("-50.00"), Decimal("-100.00"), Decimal("-150.00")]
        for i, amount in enumerate(amounts):
            txn = Transaction(
                id=str(uuid.uuid4()),
                hash=f"hash-cat-{i}",
                date=date(2024, 1, i + 1),
                amount=amount,
                raw_description=f"Test {i}",
                category_id=sample_category.id,
                account_id=sample_account.id
            )
            db_session.add(txn)
        db_session.commit()
        
        avg = get_category_average(db_session, sample_category.id, months=12)
        assert avg == 100.0  # Average of 50, 100, 150
    
    def test_only_expenses(self, db_session, sample_category, sample_account):
        """Should only average negative amounts (expenses)."""
        # Add an income transaction
        txn = Transaction(
            id=str(uuid.uuid4()),
            hash="hash-income",
            date=date(2024, 1, 1),
            amount=Decimal("500.00"),  # Positive = income
            raw_description="Refund",
            category_id=sample_category.id,
            account_id=sample_account.id
        )
        db_session.add(txn)
        db_session.commit()
        
        avg = get_category_average(db_session, sample_category.id)
        assert avg == 0.0  # Income should be excluded


class TestFirstTimeMerchant:
    """Test first-time merchant detection."""
    
    def test_new_merchant(self, db_session):
        """Should return True for unknown merchant."""
        assert is_first_time_merchant(db_session, "Brand New Store") is True
    
    def test_existing_merchant(self, db_session, sample_transaction):
        """Should return False for known merchant."""
        assert is_first_time_merchant(db_session, sample_transaction.clean_merchant) is False
    
    def test_excludes_current_transaction(self, db_session, sample_transaction):
        """Should exclude specified transaction from check."""
        # Even though merchant exists, excluding this txn makes it "new"
        result = is_first_time_merchant(
            db_session, 
            sample_transaction.clean_merchant,
            exclude_txn_id=sample_transaction.id
        )
        assert result is True


class TestPriceIncrease:
    """Test price increase detection."""
    
    def test_no_recurring_group(self, db_session):
        """Should return None if no recurring group."""
        result = check_price_increase(db_session, "Netflix", 15.99, None)
        assert result is None
    
    def test_no_expected_amount(self, db_session, sample_recurring_group):
        """Should return None if group has no expected amount."""
        sample_recurring_group.expected_amount = None
        db_session.commit()
        
        result = check_price_increase(db_session, "Netflix", 15.99, sample_recurring_group)
        assert result is None
    
    def test_no_increase(self, db_session, sample_recurring_group):
        """Should return None if amount hasn't increased."""
        result = check_price_increase(db_session, "Netflix", 15.99, sample_recurring_group)
        assert result is None
    
    def test_small_increase_ignored(self, db_session, sample_recurring_group):
        """Should return None for increases under 5%."""
        # 15.99 * 1.04 = 16.63 (4% increase)
        result = check_price_increase(db_session, "Netflix", 16.63, sample_recurring_group)
        assert result is None
    
    def test_detects_increase(self, db_session, sample_recurring_group):
        """Should detect price increase over 5%."""
        # 15.99 * 1.10 = 17.59 (10% increase)
        result = check_price_increase(db_session, "Netflix", 17.59, sample_recurring_group)
        assert result is not None
        assert result["previous_amount"] == 15.99
        assert result["new_amount"] == 17.59
        assert result["increase"] == pytest.approx(1.60, rel=0.01)


class TestAlertQueries:
    """Test alert query functions."""
    
    def test_get_alerts_empty(self, db_session):
        """Should return empty list with no alerts."""
        alerts = get_alerts(db_session)
        assert alerts == []
    
    def test_get_alerts_filters_dismissed(self, db_session):
        """Should filter out dismissed alerts by default."""
        alert = Alert(
            id=str(uuid.uuid4()),
            type=AlertType.large_purchase,
            severity=Severity.warning,
            title="Test",
            description="Test alert",
            is_dismissed=True
        )
        db_session.add(alert)
        db_session.commit()
        
        alerts = get_alerts(db_session)
        assert len(alerts) == 0
    
    def test_get_unread_count(self, db_session):
        """Should count unread, non-dismissed alerts."""
        # Add 2 unread, 1 read
        for i in range(2):
            db_session.add(Alert(
                id=str(uuid.uuid4()),
                type=AlertType.large_purchase,
                severity=Severity.info,
                title=f"Unread {i}",
                description="Test",
                is_read=False
            ))
        db_session.add(Alert(
            id=str(uuid.uuid4()),
            type=AlertType.large_purchase,
            severity=Severity.info,
            title="Read",
            description="Test",
            is_read=True
        ))
        db_session.commit()
        
        count = get_unread_count(db_session)
        assert count == 2
    
    def test_mark_all_read(self, db_session):
        """Should mark all alerts as read."""
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
        
        updated = mark_all_read(db_session)
        assert updated == 3
        assert get_unread_count(db_session) == 0
```

**Verify:**
```bash
docker compose exec api pytest tests/test_alerts_service.py -v
```

---

### Step 7: Backend - API Endpoint Tests

Create `backend/tests/test_api_health.py`:

```python
"""Tests for health check endpoint."""

def test_health_check(client):
    """Health endpoint should return ok status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app_name" in data
```

Create `backend/tests/test_api_accounts.py`:

```python
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
        response = client.post("/api/v1/accounts", json={
            "name": "My Checking",
            "account_type": "bank"
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
```

Create `backend/tests/test_api_categories.py`:

```python
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
        assert response.status_code == 200
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
        assert response.status_code == 200
        data = response.json()
        assert data["parent_id"] == sample_category.id
```

Create `backend/tests/test_api_transactions.py`:

```python
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
```

Create `backend/tests/test_api_alerts.py`:

```python
"""Tests for alerts API endpoints."""

import pytest
import uuid

from app.models.alert import Alert, AlertType, Severity


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
```

---

### Step 8: Verify All Tests Pass

```bash
# Run all tests
docker compose exec api pytest -v

# Run with coverage (optional)
docker compose exec api pytest --cov=app --cov-report=term-missing

# Expected output: All tests should pass
```

---

## Verification Checklist

- [ ] `pytest -v` runs without errors
- [ ] Deduplication tests pass (hash generation, duplicate detection)
- [ ] Recurring service tests pass (date calculations)
- [ ] Alerts service tests pass (thresholds, queries)
- [ ] API endpoint tests pass (CRUD operations)
- [ ] No import errors or fixture issues

---

## Adding Tests to Future Phases

For future phase prompts, include a testing step after implementation:

```markdown
### Step N: Add Tests for New Features

Create/update tests for the new functionality:

**Test file:** `backend/tests/test_[feature].py`

Test cases to cover:
- Happy path for main functions
- Edge cases (empty data, invalid input)
- API endpoints return expected shapes

Run and verify:
```bash
docker compose exec api pytest tests/test_[feature].py -v
```
```

This establishes testing as a standard part of each phase.
