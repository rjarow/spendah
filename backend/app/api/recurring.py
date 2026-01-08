"""API endpoints for recurring transaction management."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.recurring import RecurringGroup
from app.schemas.recurring import (
    RecurringGroupResponse,
    RecurringGroupUpdate,
    RecurringGroupCreate,
    MarkRecurringRequest,
    DetectionResponse,
    DetectionResult,
)
from app.services import recurring_service

router = APIRouter(prefix="/recurring", tags=["recurring"])


@router.get("", response_model=List[RecurringGroupResponse])
def get_recurring_groups(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Get all recurring groups."""
    groups = recurring_service.get_recurring_groups(db, include_inactive)

    # Add transaction counts
    result = []
    for group in groups:
        response = RecurringGroupResponse.model_validate(group)
        response.transaction_count = recurring_service.get_group_transaction_count(db, group.id)
        result.append(response)

    return result


@router.get("/{group_id}", response_model=RecurringGroupResponse)
def get_recurring_group(
    group_id: str,
    db: Session = Depends(get_db)
):
    """Get a single recurring group."""
    group = db.query(RecurringGroup).filter(RecurringGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Recurring group not found")

    response = RecurringGroupResponse.model_validate(group)
    response.transaction_count = recurring_service.get_group_transaction_count(db, group.id)
    return response


@router.post("", response_model=RecurringGroupResponse)
def create_recurring_group(
    data: RecurringGroupCreate,
    db: Session = Depends(get_db)
):
    """Manually create a recurring group."""
    import uuid

    group = RecurringGroup(
        id=str(uuid.uuid4()),
        name=data.name,
        merchant_pattern=data.merchant_pattern,
        expected_amount=data.expected_amount,
        amount_variance=data.amount_variance,
        frequency=data.frequency,
        category_id=data.category_id,
        is_active=True,
    )
    db.add(group)
    db.commit()
    db.refresh(group)

    response = RecurringGroupResponse.model_validate(group)
    response.transaction_count = 0
    return response


@router.patch("/{group_id}", response_model=RecurringGroupResponse)
def update_recurring_group(
    group_id: str,
    update: RecurringGroupUpdate,
    db: Session = Depends(get_db)
):
    """Update a recurring group."""
    group = db.query(RecurringGroup).filter(RecurringGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Recurring group not found")

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(group, field, value)

    db.commit()
    db.refresh(group)

    response = RecurringGroupResponse.model_validate(group)
    response.transaction_count = recurring_service.get_group_transaction_count(db, group.id)
    return response


@router.delete("/{group_id}")
def delete_recurring_group(
    group_id: str,
    db: Session = Depends(get_db)
):
    """Delete a recurring group (unlinks transactions but doesn't delete them)."""
    group = db.query(RecurringGroup).filter(RecurringGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Recurring group not found")

    # Unlink all transactions
    from app.models.transaction import Transaction
    db.query(Transaction).filter(
        Transaction.recurring_group_id == group_id
    ).update(
        {Transaction.recurring_group_id: None, Transaction.is_recurring: False},
        synchronize_session=False
    )

    db.delete(group)
    db.commit()

    return {"deleted": True}


@router.post("/detect", response_model=DetectionResponse)
async def detect_recurring(
    db: Session = Depends(get_db)
):
    """
    Use AI to detect recurring patterns in transaction history.
    Returns detected patterns without creating groups yet.
    """
    import sys
    print("DEBUG: detect_recurring endpoint called", file=sys.stderr)
    patterns = await recurring_service.detect_recurring_patterns(db)

    detected = [
        DetectionResult(
            merchant_pattern=p["merchant_pattern"],
            suggested_name=p["suggested_name"],
            transaction_ids=p.get("transaction_ids", []),
            frequency=p["frequency"],
            average_amount=abs(p["average_amount"]),
            confidence=p["confidence"],
        )
        for p in patterns
    ]

    return DetectionResponse(
        detected=detected,
        total_found=len(detected)
    )


@router.post("/detect/apply")
async def apply_detection(
    detection_index: int = Query(..., description="Index of detection to apply"),
    db: Session = Depends(get_db)
):
    """
    Apply a specific detection result - create recurring group and link transactions.
    Run /detect first, then call this with index of pattern to apply.
    """
    # Re-run detection to get fresh results
    patterns = await recurring_service.detect_recurring_patterns(db)

    if detection_index < 0 or detection_index >= len(patterns):
        raise HTTPException(status_code=400, detail="Invalid detection index")

    detection = patterns[detection_index]
    group = recurring_service.create_recurring_group_from_detection(db, detection)

    response = RecurringGroupResponse.model_validate(group)
    response.transaction_count = len(detection.get("transaction_ids", []))
    return response


@router.post("/transactions/{transaction_id}/mark")
def mark_transaction_recurring(
    transaction_id: str,
    request: MarkRecurringRequest,
    db: Session = Depends(get_db)
):
    """Mark a transaction as recurring."""
    try:
        group = recurring_service.mark_transaction_recurring(
            db=db,
            transaction_id=transaction_id,
            recurring_group_id=request.recurring_group_id,
            create_new=request.create_new,
            new_name=request.name,
            new_frequency=request.frequency if request.frequency else None,
        )
        response = RecurringGroupResponse.model_validate(group)
        response.transaction_count = recurring_service.get_group_transaction_count(db, group.id)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/transactions/{transaction_id}/unmark")
def unmark_transaction_recurring(
    transaction_id: str,
    db: Session = Depends(get_db)
):
    """Remove a transaction from its recurring group."""
    recurring_service.unmark_transaction_recurring(db, transaction_id)
    return {"success": True}
