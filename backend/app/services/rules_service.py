"""
Rules service for categorization rule matching and generation.
"""

import re
import logging
from typing import Optional, List, Dict, Any
from collections import Counter
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.rule import CategorizationRule, MatchField, MatchType
from app.models.category import Category
from app.models.user_correction import UserCorrection
from app.schemas.rules import RuleSuggestion

logger = logging.getLogger(__name__)

_rules_cache: Optional[List[CategorizationRule]] = None
_cache_valid = False


def invalidate_cache():
    """Invalidate the rules cache."""
    global _rules_cache, _cache_valid
    _cache_valid = False


def load_rules(db: Session, use_cache: bool = True) -> List[CategorizationRule]:
    """Load all active rules ordered by priority."""
    global _rules_cache, _cache_valid

    if use_cache and _cache_valid and _rules_cache is not None:
        return _rules_cache

    _rules_cache = (
        db.query(CategorizationRule)
        .filter(CategorizationRule.is_active == True)
        .order_by(CategorizationRule.priority.asc())
        .all()
    )
    _cache_valid = True
    return _rules_cache


def match_rule(
    rule: CategorizationRule,
    merchant: Optional[str],
    description: str,
    amount: Optional[float],
) -> bool:
    """Check if a rule matches the given transaction data."""
    match_value = rule.match_value

    if rule.match_field == MatchField.merchant:
        text = merchant or description
    elif rule.match_field == MatchField.description:
        text = description
    elif rule.match_field == MatchField.amount:
        if amount is None:
            return False
        try:
            target_amount = float(match_value)
            return abs(amount - target_amount) < 0.01
        except ValueError:
            return False
    else:
        return False

    text = text.lower()
    match_value_lower = match_value.lower()

    if rule.match_type == MatchType.contains:
        return match_value_lower in text
    elif rule.match_type == MatchType.exact:
        return text == match_value_lower
    elif rule.match_type == MatchType.starts_with:
        return text.startswith(match_value_lower)
    elif rule.match_type == MatchType.regex:
        try:
            return bool(re.search(match_value, text, re.IGNORECASE))
        except re.error:
            logger.warning(f"Invalid regex in rule {rule.id}: {match_value}")
            return False

    return False


def apply_rules(
    db: Session,
    merchant: Optional[str],
    description: str,
    amount: Optional[float] = None,
    use_cache: bool = True,
) -> Optional[str]:
    """
    Apply categorization rules to a transaction.

    Returns category_id if a rule matches, None otherwise.
    """
    rules = load_rules(db, use_cache=use_cache)

    for rule in rules:
        if match_rule(rule, merchant, description, amount):
            rule.match_count += 1
            db.commit()
            logger.debug(f"Rule '{rule.name}' matched for: {merchant or description}")
            return rule.category_id

    return None


def generate_rules_from_corrections(
    db: Session, min_occurrences: int = 3
) -> List[RuleSuggestion]:
    """
    Generate rule suggestions from user correction patterns.

    Groups corrections by (clean_merchant, category_id) and suggests rules
    for patterns that appear min_occurrences or more times.
    """
    corrections = db.query(UserCorrection).all()

    pattern_counts: Dict[tuple, Counter] = {}

    for correction in corrections:
        key = (correction.clean_merchant, correction.category_id)
        if key not in pattern_counts:
            pattern_counts[key] = Counter()
        pattern_counts[key][correction.raw_description] += 1

    categories = {str(c.id): c.name for c in db.query(Category).all()}

    suggestions = []

    for (clean_merchant, category_id), raw_descriptions in pattern_counts.items():
        total_count = sum(raw_descriptions.values())

        if total_count >= min_occurrences:
            most_common_raw = raw_descriptions.most_common(1)[0][0]

            suggestion = RuleSuggestion(
                name=f"{clean_merchant} → {categories.get(category_id, 'Unknown')}",
                match_field="merchant",
                match_type="contains",
                match_value=clean_merchant,
                category_id=category_id,
                category_name=categories.get(category_id, "Unknown"),
                occurrence_count=total_count,
            )
            suggestions.append(suggestion)

    suggestions.sort(key=lambda s: s.occurrence_count, reverse=True)

    return suggestions


def create_rule_from_correction(
    db: Session,
    clean_merchant: str,
    category_id: str,
) -> CategorizationRule:
    """
    Create a rule from a user correction.

    Auto-creates a contains rule for the merchant.
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    category_name = category.name if category else "Unknown"

    rule = CategorizationRule(
        name=f"{clean_merchant} → {category_name}",
        match_field=MatchField.merchant,
        match_type=MatchType.contains,
        match_value=clean_merchant,
        category_id=category_id,
        priority=100,
        is_active=True,
        auto_created=True,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    invalidate_cache()

    logger.info(f"Created auto-rule: {rule.name}")
    return rule
