"""
Rules API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.dependencies import get_db
from app.models.rule import CategorizationRule, MatchField, MatchType
from app.models.category import Category
from app.schemas.rules import (
    RuleCreate,
    RuleUpdate,
    RuleResponse,
    RuleListResponse,
    RuleTestRequest,
    RuleTestResponse,
    RuleSuggestionsResponse,
)
from app.services import rules_service

router = APIRouter(prefix="/rules", tags=["rules"])


def rule_to_response(rule: CategorizationRule, category_name: str) -> RuleResponse:
    """Convert a rule model to response schema."""
    return RuleResponse(
        id=str(rule.id),
        name=rule.name,
        match_field=rule.match_field.value
        if isinstance(rule.match_field, MatchField)
        else rule.match_field,
        match_type=rule.match_type.value
        if isinstance(rule.match_type, MatchType)
        else rule.match_type,
        match_value=rule.match_value,
        category_id=str(rule.category_id),
        category_name=category_name,
        priority=rule.priority,
        is_active=rule.is_active,
        auto_created=rule.auto_created,
        match_count=rule.match_count,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.get("", response_model=RuleListResponse)
def list_rules(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """List all categorization rules, ordered by priority."""
    query = db.query(CategorizationRule)

    if is_active is not None:
        query = query.filter(CategorizationRule.is_active == is_active)

    rules = query.order_by(CategorizationRule.priority.asc()).all()

    category_ids = {str(r.category_id) for r in rules}
    categories = {
        str(c.id): c.name
        for c in db.query(Category).filter(Category.id.in_(category_ids)).all()
    }

    items = [
        rule_to_response(r, categories.get(str(r.category_id), "Unknown"))
        for r in rules
    ]

    return RuleListResponse(items=items, total=len(items))


@router.post("", response_model=RuleResponse)
def create_rule(data: RuleCreate, db: Session = Depends(get_db)):
    """Create a new categorization rule."""
    category = db.query(Category).filter(Category.id == data.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    rule = CategorizationRule(
        name=data.name,
        match_field=MatchField(
            data.match_field.value
            if hasattr(data.match_field, "value")
            else data.match_field
        ),
        match_type=MatchType(
            data.match_type.value
            if hasattr(data.match_type, "value")
            else data.match_type
        ),
        match_value=data.match_value,
        category_id=data.category_id,
        priority=data.priority,
        is_active=data.is_active,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    rules_service.invalidate_cache()

    return rule_to_response(rule, category.name)


@router.get("/{rule_id}", response_model=RuleResponse)
def get_rule(rule_id: str, db: Session = Depends(get_db)):
    """Get a specific rule."""
    rule = db.query(CategorizationRule).filter(CategorizationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    category = db.query(Category).filter(Category.id == rule.category_id).first()
    category_name = category.name if category else "Unknown"

    return rule_to_response(rule, category_name)


@router.patch("/{rule_id}", response_model=RuleResponse)
def update_rule(rule_id: str, data: RuleUpdate, db: Session = Depends(get_db)):
    """Update a rule."""
    rule = db.query(CategorizationRule).filter(CategorizationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    update_data = data.model_dump(exclude_unset=True)

    if "match_field" in update_data and update_data["match_field"] is not None:
        update_data["match_field"] = MatchField(
            update_data["match_field"].value
            if hasattr(update_data["match_field"], "value")
            else update_data["match_field"]
        )

    if "match_type" in update_data and update_data["match_type"] is not None:
        update_data["match_type"] = MatchType(
            update_data["match_type"].value
            if hasattr(update_data["match_type"], "value")
            else update_data["match_type"]
        )

    if "category_id" in update_data and update_data["category_id"] is not None:
        category = (
            db.query(Category).filter(Category.id == update_data["category_id"]).first()
        )
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

    for key, value in update_data.items():
        setattr(rule, key, value)

    db.commit()
    db.refresh(rule)

    rules_service.invalidate_cache()

    category = db.query(Category).filter(Category.id == rule.category_id).first()
    category_name = category.name if category else "Unknown"

    return rule_to_response(rule, category_name)


@router.delete("/{rule_id}")
def delete_rule(rule_id: str, db: Session = Depends(get_db)):
    """Delete a rule."""
    rule = db.query(CategorizationRule).filter(CategorizationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    db.delete(rule)
    db.commit()

    rules_service.invalidate_cache()

    return {"status": "deleted"}


@router.post("/test", response_model=RuleTestResponse)
def test_rule(request: RuleTestRequest, db: Session = Depends(get_db)):
    """Test a string against all active rules."""
    rules = rules_service.load_rules(db)

    for rule in rules:
        if rules_service.match_rule(rule, None, request.text, request.amount):
            category = (
                db.query(Category).filter(Category.id == rule.category_id).first()
            )
            category_name = category.name if category else "Unknown"
            return RuleTestResponse(
                matched=True,
                rule=rule_to_response(rule, category_name),
            )

    return RuleTestResponse(matched=False, rule=None)


@router.post("/generate-from-corrections", response_model=RuleSuggestionsResponse)
def generate_from_corrections(
    min_occurrences: int = 3,
    db: Session = Depends(get_db),
):
    """Generate rule suggestions from user correction patterns."""
    suggestions = rules_service.generate_rules_from_corrections(db, min_occurrences)
    return RuleSuggestionsResponse(suggestions=suggestions, total=len(suggestions))


@router.post("/create-from-suggestion", response_model=RuleResponse)
def create_from_suggestion(
    suggestion_index: int,
    db: Session = Depends(get_db),
):
    """Create a rule from a suggestion by index."""
    suggestions = rules_service.generate_rules_from_corrections(db)

    if suggestion_index < 0 or suggestion_index >= len(suggestions):
        raise HTTPException(status_code=400, detail="Invalid suggestion index")

    suggestion = suggestions[suggestion_index]

    existing = (
        db.query(CategorizationRule)
        .filter(
            CategorizationRule.match_value == suggestion.match_value,
            CategorizationRule.category_id == suggestion.category_id,
        )
        .first()
    )

    if existing:
        category = (
            db.query(Category).filter(Category.id == existing.category_id).first()
        )
        return rule_to_response(existing, category.name if category else "Unknown")

    rule = CategorizationRule(
        name=suggestion.name,
        match_field=MatchField.merchant,
        match_type=MatchType.contains,
        match_value=suggestion.match_value,
        category_id=suggestion.category_id,
        priority=100,
        is_active=True,
        auto_created=True,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    rules_service.invalidate_cache()

    return rule_to_response(rule, suggestion.category_name)
