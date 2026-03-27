"""
Budget API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.dependencies import get_db
from app.models import Budget, Category, Transaction
from app.schemas.budget import (
    BudgetCreate,
    BudgetUpdate,
    BudgetResponse,
    BudgetList,
    BudgetProgress,
)
from app.services.budget_service import get_budget_progress, get_all_budgets_progress
from app.services.budget_alerts import check_all_budget_alerts

router = APIRouter(tags=["budgets"])


@router.get("")
def list_budgets(
    include_progress: bool = Query(False, description="Include progress calculations"),
    db: Session = Depends(get_db),
):
    """List all active budgets."""
    budgets = db.query(Budget).filter(Budget.is_active == True).all()

    if include_progress:
        progress_list = get_all_budgets_progress(db)
        return {"items": progress_list, "total": len(progress_list)}

    items = []
    for budget in budgets:
        items.append(BudgetResponse(**budget.__dict__, category=budget.category))

    return BudgetList(items=items, total=len(items))


@router.post("", response_model=BudgetResponse, status_code=201)
def create_budget(budget: BudgetCreate, db: Session = Depends(get_db)):
    """Create a new budget."""
    # Validate category if provided
    if budget.category_id:
        category = db.query(Category).filter(Category.id == budget.category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

    db_budget = Budget(
        category_id=budget.category_id,
        amount=budget.amount,
        period=budget.period,
        start_date=budget.start_date or datetime.utcnow(),
        is_active=budget.is_active,
    )
    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)
    return db_budget


@router.get("/{budget_id}", response_model=BudgetResponse)
def get_budget(budget_id: str, db: Session = Depends(get_db)):
    """Get a specific budget."""
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return budget


@router.get("/{budget_id}/progress", response_model=BudgetProgress)
def get_budget_progress_endpoint(
    budget_id: str, date: Optional[str] = None, db: Session = Depends(get_db)
):
    """
    Get budget with progress calculation.

    Optional date parameter allows viewing historical periods.
    If not provided, shows current period.
    """
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    # Parse date if provided (for historical views)
    as_of_date = None
    if date:
        try:
            from datetime import datetime

            as_of_date = datetime.fromisoformat(date)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use ISO format (YYYY-MM-DD)",
            )

    progress_data = get_budget_progress(db, budget_id, as_of_date)
    if not progress_data:
        raise HTTPException(status_code=404, detail="Budget not found")

    return BudgetProgress(**progress_data)


@router.patch("/{budget_id}", response_model=BudgetResponse)
def update_budget(
    budget_id: str, budget_update: BudgetUpdate, db: Session = Depends(get_db)
):
    """Update a budget."""
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    # Validate category if provided
    if budget_update.category_id is not None:
        category = (
            db.query(Category).filter(Category.id == budget_update.category_id).first()
        )
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

    # Update fields if provided
    if budget_update.amount is not None:
        budget.amount = budget_update.amount
    if budget_update.period is not None:
        budget.period = budget_update.period
    if budget_update.start_date is not None:
        budget.start_date = budget_update.start_date
    if budget_update.is_active is not None:
        budget.is_active = budget_update.is_active

    # Update timestamp
    budget.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(budget)
    return budget


@router.delete("/{budget_id}", status_code=204)
def delete_budget(budget_id: str, db: Session = Depends(get_db)):
    """Soft delete a budget (set is_active to False)."""
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    # Soft delete
    budget.is_active = False
    db.commit()
    return None


@router.post("/check-alerts", status_code=200)
def check_budget_alerts(db: Session = Depends(get_db)):
    """
    Manually trigger budget alert check for all active budgets.
    This can be called via cron or as part of transaction processing.
    """
    try:
        alerts = check_all_budget_alerts(db)
        return {
            "message": f"Checked {len(alerts)} budgets for alerts",
            "created_alerts": len(alerts),
            "alerts": [
                {
                    "id": str(alert.id),
                    "type": alert.type.value,
                    "severity": alert.severity.value,
                    "title": alert.title,
                }
                for alert in alerts
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Budget alert check failed: {e}")
