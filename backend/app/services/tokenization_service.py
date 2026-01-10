"""Service for tokenizing PII before AI calls and de-tokenizing responses."""

import re
import random
from datetime import date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session

from app.models.token_map import TokenMap, TokenType, DateShift
from app.models.privacy_settings import get_or_create_privacy_settings


class TokenizationService:
    """
    Handles tokenization and de-tokenization of PII.
    
    Tokens are deterministic and persistent - the same input always produces
    the same token across sessions.
    """

    # Patterns for extracting person names from descriptions
    PERSON_PATTERNS = [
        (r'VENMO\s+(?:PAYMENT\s+)?([A-Z][A-Z\s]+)', 'VENMO'),
        (r'ZELLE\s+(?:PAYMENT\s+)?(?:TO\s+|FROM\s+)?([A-Z][A-Z\s]+)', 'ZELLE'),
        (r'PAYPAL\s+\*([A-Z][A-Z\s]+)', 'PAYPAL'),
        (r'CASH\s+APP\s+\*([A-Z][A-Z\s]+)', 'CASH APP'),
    ]

    def __init__(self, db: Session):
        self.db = db
        self._cache: Dict[Tuple[TokenType, str], str] = {}
        self._reverse_cache: Dict[str, str] = {}
        self._load_caches()
        self._date_shift: Optional[int] = None

    def _load_caches(self):
        """Load existing token mappings into memory."""
        tokens = self.db.query(TokenMap).all()
        for t in tokens:
            key = (t.token_type, t.normalized_value)
            self._cache[key] = t.token
            self._reverse_cache[t.token] = t.original_value

    def _get_date_shift(self) -> int:
        """Get or create the date shift value."""
        if self._date_shift is not None:
            return self._date_shift

        shift_record = self.db.query(DateShift).first()
        if shift_record:
            self._date_shift = shift_record.shift_days
        else:
            # Generate random shift between 500-1500 days
            self._date_shift = random.randint(500, 1500)
            shift_record = DateShift(id=1, shift_days=self._date_shift)
            self.db.add(shift_record)
            self.db.commit()

        return self._date_shift

    def _normalize(self, value: str) -> str:
        """Normalize a value for consistent matching."""
        return value.strip().upper()

    def _get_next_token_number(self, token_type: TokenType) -> int:
        """Get the next available token number for a type."""
        count = self.db.query(TokenMap).filter(
            TokenMap.token_type == token_type
        ).count()
        return count + 1

    def tokenize_merchant(
        self,
        merchant: str,
        category: Optional[str] = None,
        subcategory: Optional[str] = None
    ) -> str:
        """
        Tokenize a merchant name.

        Returns: Token like "MERCHANT_042"
        """
        normalized = self._normalize(merchant)
        cache_key = (TokenType.merchant, normalized)

        # Check cache first
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Check database
        existing = self.db.query(TokenMap).filter(
            TokenMap.token_type == TokenType.merchant,
            TokenMap.normalized_value == normalized
        ).first()

        if existing:
            self._cache[cache_key] = existing.token
            self._reverse_cache[existing.token] = existing.original_value
            return existing.token

        # Create new token
        token_num = self._get_next_token_number(TokenType.merchant)
        token = f"MERCHANT_{token_num:04d}"

        metadata = {}
        if category:
            metadata["category"] = category
        if subcategory:
            metadata["subcategory"] = subcategory

        token_map = TokenMap(
            token_type=TokenType.merchant,
            original_value=merchant,
            normalized_value=normalized,
            token=token,
            metadata_=metadata if metadata else None
        )
        self.db.add(token_map)
        self.db.commit()

        self._cache[cache_key] = token
        self._reverse_cache[token] = merchant

        return token

    def tokenize_account(
        self,
        account_name: str,
        account_type: Optional[str] = None
    ) -> str:
        """Tokenize an account identifier."""
        normalized = self._normalize(account_name)
        cache_key = (TokenType.account, normalized)

        if cache_key in self._cache:
            return self._cache[cache_key]

        existing = self.db.query(TokenMap).filter(
            TokenMap.token_type == TokenType.account,
            TokenMap.normalized_value == normalized
        ).first()

        if existing:
            self._cache[cache_key] = existing.token
            self._reverse_cache[existing.token] = existing.original_value
            return existing.token

        token_num = self._get_next_token_number(TokenType.account)
        token = f"ACCOUNT_{token_num:03d}"

        metadata = {"account_type": account_type} if account_type else None

        token_map = TokenMap(
            token_type=TokenType.account,
            original_value=account_name,
            normalized_value=normalized,
            token=token,
            metadata_=metadata
        )
        self.db.add(token_map)
        self.db.commit()

        self._cache[cache_key] = token
        self._reverse_cache[token] = account_name

        return token

    def tokenize_description(self, description: str) -> str:
        """
        Tokenize person names within a description.

        Example: "VENMO JOHN SMITH" -> "VENMO PERSON_001"
        """
        result = description

        for pattern, service in self.PERSON_PATTERNS:
            match = re.search(pattern, description.upper())
            if match:
                person_name = match.group(1).strip()
                person_token = self._tokenize_person(person_name)
                # Replace the person name portion
                result = re.sub(
                    pattern,
                    f"{service} {person_token}",
                    result,
                    flags=re.IGNORECASE
                )

        return result

    def _tokenize_person(self, person_name: str) -> str:
        """Tokenize a person's name."""
        normalized = self._normalize(person_name)
        cache_key = (TokenType.person, normalized)

        if cache_key in self._cache:
            return self._cache[cache_key]

        existing = self.db.query(TokenMap).filter(
            TokenMap.token_type == TokenType.person,
            TokenMap.normalized_value == normalized
        ).first()

        if existing:
            self._cache[cache_key] = existing.token
            self._reverse_cache[existing.token] = existing.original_value
            return existing.token

        token_num = self._get_next_token_number(TokenType.person)
        token = f"PERSON_{token_num:03d}"

        token_map = TokenMap(
            token_type=TokenType.person,
            original_value=person_name,
            normalized_value=normalized,
            token=token,
            metadata_=None
        )
        self.db.add(token_map)
        self.db.commit()

        self._cache[cache_key] = token
        self._reverse_cache[token] = person_name

        return token

    def shift_date(self, original_date: date) -> date:
        """Shift a date by the installation's random offset."""
        shift = self._get_date_shift()
        return original_date + timedelta(days=shift)

    def unshift_date(self, shifted_date: date) -> date:
        """Reverse date shift for display."""
        shift = self._get_date_shift()
        return shifted_date - timedelta(days=shift)

    def detokenize(self, text: str) -> str:
        """
        Replace all tokens in text with original values.

        Used for displaying AI responses to users.
        """
        result = text

        # Find all tokens in the text
        token_pattern = r'(MERCHANT_\d{4}|ACCOUNT_\d{3}|PERSON_\d{3})'

        for match in re.finditer(token_pattern, text):
            token = match.group(1)
            if token in self._reverse_cache:
                result = result.replace(token, self._reverse_cache[token])

        return result

    def tokenize_transaction_for_ai(
        self,
        transaction: Dict[str, Any],
        include_category: bool = True
    ) -> Dict[str, Any]:
        """
        Tokenize a transaction dict for sending to AI.

        Input: {"merchant": "Whole Foods", "amount": -187.34, "date": "2024-01-15", ...}
        Output: {"merchant": "MERCHANT_042 [Groceries]", "amount": -187.34, "date": "2026-08-09", ...}
        """
        result = dict(transaction)

        # Tokenize merchant
        if "merchant" in result or "clean_merchant" in result:
            merchant = result.get("clean_merchant") or result.get("merchant", "")
            category = result.get("category_name") if include_category else None
            token = self.tokenize_merchant(merchant, category)

            if include_category and category:
                result["merchant"] = f"{token} [{category}]"
            else:
                result["merchant"] = token

            # Remove raw fields
            result.pop("clean_merchant", None)
            result.pop("raw_description", None)

        # Tokenize description if present
        if "description" in result:
            result["description"] = self.tokenize_description(result["description"])

        # Shift date
        if "date" in result:
            if isinstance(result["date"], str):
                from datetime import datetime
                d = datetime.fromisoformat(result["date"]).date()
            else:
                d = result["date"]
            result["date"] = self.shift_date(d).isoformat()

        # Tokenize account if present
        if "account_name" in result:
            account_type = result.get("account_type")
            result["account"] = self.tokenize_account(result["account_name"], account_type)
            result.pop("account_name", None)
            result.pop("account_type", None)

        return result

    def get_unknown_merchants(self, merchants: List[str]) -> List[str]:
        """
        Filter to only merchants not yet in token map.

        Used for bulk categorization - only send new merchants to AI.
        """
        unknown = []
        for merchant in merchants:
            normalized = self._normalize(merchant)
            cache_key = (TokenType.merchant, normalized)
            if cache_key not in self._cache:
                # Double-check database
                existing = self.db.query(TokenMap).filter(
                    TokenMap.token_type == TokenType.merchant,
                    TokenMap.normalized_value == normalized
                ).first()
                if not existing:
                    unknown.append(merchant)

        return unknown

    def get_token_stats(self) -> Dict[str, int]:
        """Get counts of each token type."""
        stats = {}
        for token_type in TokenType:
            count = self.db.query(TokenMap).filter(
                TokenMap.token_type == token_type
            ).count()
            stats[token_type.value] = count

        # Add date shift info
        shift = self.db.query(DateShift).first()
        stats["date_shift_days"] = shift.shift_days if shift else 0

        return stats
