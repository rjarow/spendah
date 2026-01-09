"""Tests for transaction deduplication logic."""

import pytest
from datetime import date
from decimal import Decimal

from app.services.deduplication_service import generate_transaction_hash, is_duplicate
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
