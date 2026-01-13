"""Tests for tokenization service."""

import pytest
from datetime import date
from app.services.tokenization_service import TokenizationService
from app.models.token_map import TokenMap, TokenType, DateShift


class TestMerchantTokenization:
    """Tests for merchant tokenization."""

    def test_same_merchant_same_token(self, db_session):
        """Same merchant should always get same token."""
        service = TokenizationService(db_session)

        token1 = service.tokenize_merchant("Whole Foods")
        token2 = service.tokenize_merchant("Whole Foods")

        assert token1 == token2

    def test_case_insensitive(self, db_session):
        """Tokenization should be case-insensitive."""
        service = TokenizationService(db_session)

        token1 = service.tokenize_merchant("whole foods")
        token2 = service.tokenize_merchant("WHOLE FOODS")
        token3 = service.tokenize_merchant("Whole Foods")

        assert token1 == token2 == token3

    def test_different_merchants_different_tokens(self, db_session):
        """Different merchants should get different tokens."""
        service = TokenizationService(db_session)

        token1 = service.tokenize_merchant("Whole Foods")
        token2 = service.tokenize_merchant("Trader Joes")

        assert token1 != token2

    def test_token_format(self, db_session):
        """Token should match expected format."""
        service = TokenizationService(db_session)

        token = service.tokenize_merchant("Test Merchant")

        assert token.startswith("MERCHANT_")
        assert len(token) == 13

    def test_category_metadata_stored(self, db_session):
        """Category metadata should be stored with token."""
        service = TokenizationService(db_session)

        token = service.tokenize_merchant("Whole Foods", category="Groceries", subcategory="Supermarket")

        token_map = db_session.query(TokenMap).filter(TokenMap.token == token).first()
        assert token_map.metadata_["category"] == "Groceries"
        assert token_map.metadata_["subcategory"] == "Supermarket"


class TestPersonTokenization:
    """Tests for person name tokenization in descriptions."""

    def test_venmo_extraction(self, db_session):
        """Should extract and tokenize Venmo names."""
        service = TokenizationService(db_session)

        result = service.tokenize_description("VENMO PAYMENT JOHN SMITH")

        assert "VENMO" in result
        assert "PERSON_" in result
        assert "JOHN SMITH" not in result

    def test_zelle_extraction(self, db_session):
        """Should extract and tokenize Zelle names."""
        service = TokenizationService(db_session)

        result = service.tokenize_description("ZELLE TO JANE DOE")

        assert "ZELLE" in result
        assert "PERSON_" in result
        assert "JANE DOE" not in result

    def test_same_person_same_token(self, db_session):
        """Same person should get same token."""
        service = TokenizationService(db_session)

        result1 = service.tokenize_description("VENMO JOHN SMITH")
        result2 = service.tokenize_description("ZELLE TO JOHN SMITH")

        # Extract tokens
        import re
        tokens1 = re.findall(r'PERSON_\d+', result1)
        tokens2 = re.findall(r'PERSON_\d+', result2)

        assert tokens1[0] == tokens2[0]


class TestDateShifting:
    """Tests for date shifting."""

    def test_date_shifted(self, db_session):
        """Dates should be shifted by random offset."""
        service = TokenizationService(db_session)

        original = date(2024, 1, 15)
        shifted = service.shift_date(original)

        assert shifted != original
        assert shifted > original

    def test_consistent_shift(self, db_session):
        """Same date should always shift the same amount."""
        service = TokenizationService(db_session)

        original = date(2024, 1, 15)
        shifted1 = service.shift_date(original)
        shifted2 = service.shift_date(original)

        assert shifted1 == shifted2

    def test_unshift_reverses(self, db_session):
        """Unshift should reverse the shift."""
        service = TokenizationService(db_session)

        original = date(2024, 1, 15)
        shifted = service.shift_date(original)
        unshifted = service.unshift_date(shifted)

        assert unshifted == original


class TestDetokenization:
    """Tests for de-tokenizing AI responses."""

    def test_detokenize_merchant(self, db_session):
        """Should replace merchant tokens with original values."""
        service = TokenizationService(db_session)

        # First, create a token
        token = service.tokenize_merchant("Whole Foods")

        # Then detokenize text containing it
        text = f"You spent $100 at {token} last month."
        result = service.detokenize(text)

        assert "Whole Foods" in result
        assert token not in result

    def test_detokenize_multiple_tokens(self, db_session):
        """Should handle multiple tokens in text."""
        service = TokenizationService(db_session)

        token1 = service.tokenize_merchant("Whole Foods")
        token2 = service.tokenize_merchant("Trader Joes")

        text = f"Compare {token1} vs {token2}"
        result = service.detokenize(text)

        assert "Whole Foods" in result
        assert "Trader Joes" in result


class TestBulkOperations:
    """Tests for bulk tokenization operations."""

    def test_get_unknown_merchants(self, db_session):
        """Should filter to only unknown merchants."""
        service = TokenizationService(db_session)

        # Create some known merchants
        service.tokenize_merchant("Whole Foods")
        service.tokenize_merchant("Trader Joes")

        # Check which are unknown
        merchants = ["Whole Foods", "Target", "Costco", "Trader Joes"]
        unknown = service.get_unknown_merchants(merchants)

        assert "Target" in unknown
        assert "Costco" in unknown
        assert "Whole Foods" not in unknown
        assert "Trader Joes" not in unknown

    def test_tokenize_transaction(self, db_session):
        """Should tokenize full transaction dict."""
        service = TokenizationService(db_session)

        transaction = {
            "clean_merchant": "Whole Foods",
            "amount": -187.34,
            "date": "2024-01-15",
            "category_name": "Groceries",
            "account_name": "Chase Checking",
            "account_type": "checking",
        }

        result = service.tokenize_transaction_for_ai(transaction)

        assert result["merchant"].startswith("MERCHANT_")
        assert "[Groceries]" in result["merchant"]
        assert result["amount"] == -187.34
        assert "2024-01-15" not in result["date"]
        assert result.get("account", "").startswith("ACCOUNT_")
        assert "clean_merchant" not in result
        assert "account_name" not in result


class TestPrivacySettings:
    """Tests for privacy settings persistence."""

    def test_settings_created_on_first_access(self, db_session):
        """Settings should be created with defaults on first access."""
        from app.models.privacy_settings import get_or_create_privacy_settings

        settings = get_or_create_privacy_settings(db_session)

        assert settings.obfuscation_enabled == True
        assert settings.ollama_obfuscation == False
        assert settings.openrouter_obfuscation == True

    def test_settings_persisted(self, db_session):
        """Settings changes should persist."""
        from app.models.privacy_settings import get_or_create_privacy_settings, PrivacySettings

        # Get and modify
        settings = get_or_create_privacy_settings(db_session)
        settings.ollama_obfuscation = True
        db_session.commit()

        # Fetch fresh
        db_session.expire(settings)
        settings2 = db_session.query(PrivacySettings).filter(PrivacySettings.id == 1).first()
        assert settings2.ollama_obfuscation == True
