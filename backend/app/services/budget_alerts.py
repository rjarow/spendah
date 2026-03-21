"""Service for budget alert detection and management."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid

from app.models.alert import Alert, AlertType, Severity, AlertSettings
from app.models.budget import Budget, BudgetPeriod
from app.models.category import Category
from app.models.transaction import Transaction
from app.services.alerts_service import get_or_create_settings


def get_budget_spending(db: Session, budget: Budget) -> Dict[str, Any]:
    """Get total spending for a budget over its active period."""
    amount = float(budget.amount)
    period = budget.period
    
    if period == BudgetPeriod.weekly:
        cutoff = datetime.now() - timedelta(days=7)
    elif period == BudgetPeriod.monthly:
        cutoff = datetime.now() - timedelta(days=30)
    else:
        cutoff = datetime.now() - timedelta(days=365)
    
    query = db.query(func.abs(func.sum(Transaction.amount))).filter(
        Transaction.amount < 0,
        Transaction.category_id == budget.category_id,
        Transaction.date >= cutoff
    )
    
    spent = query.scalar()
    if spent:
        spent = abs(float(spent))
    else:
        spent = 0.0
    
    percent_used = (spent / amount) * 100 if amount > 0 else 0
    
    return {
        "spent": spent,
        "percent_used": percent_used,
        "amount": amount
    }


def check_budget_alerts(db: Session, budget_id: str) -> Optional[Alert]:
    """
    Check a single budget for alert conditions and create alerts if needed.
    
    Triggers:
    - budget_warning: when percent_used >= 80% and < 100%
    - budget_exceeded: when percent_used >= 100%
    
    Avoids duplicate alerts by checking if similar alert exists.
    """
    budget = db.query(Budget).filter(Budget.id == budget_id, Budget.is_active == True).first()
    if not budget:
        return None
    
    settings = get_or_create_settings(db)
    if not settings.alerts_enabled:
        return None
    
    spending_data = get_budget_spending(db, budget)
    percent_used = spending_data["percent_used"]
    amount = budget.amount
    
    # Check for budget exceeded (>= 100%)
    if percent_used >= 100:
        existing_alert = db.query(Alert).filter(
            Alert.type == AlertType.budget_exceeded,
            Alert.budget_id == budget_id
        ).order_by(Alert.created_at.desc()).first()

        if existing_alert:
            return None
        
        alert = Alert(
            id=str(uuid.uuid4()),
            type=AlertType.budget_exceeded,
            severity=Severity.attention,
            title=f"Budget exceeded: {budget.category.name if budget.category else 'Uncategorized'}",
            description=f"${spending_data['spent']:.2f} of ${amount:.2f} (${percent_used:.0f}% used)",
            budget_id=budget_id,
            alert_metadata={
                "budget_id": budget_id,
                "category_id": budget.category_id,
                "category_name": budget.category.name if budget.category else "Uncategorized",
                "spent": float(spending_data['spent']),
                "limit": float(amount),
                "percent_used": percent_used,
                "period": budget.period.value
            }
        )
        db.add(alert)
        db.commit()
        return alert
    
    # Check for budget warning (>= 80% and < 100%)
    if percent_used >= 80 and percent_used < 100:
        existing_alert = db.query(Alert).filter(
            Alert.type == AlertType.budget_warning,
            Alert.budget_id == budget_id
        ).order_by(Alert.created_at.desc()).first()

        if existing_alert:
            return None
        
        alert = Alert(
            id=str(uuid.uuid4()),
            type=AlertType.budget_warning,
            severity=Severity.warning,
            title=f"Budget approaching limit: {budget.category.name if budget.category else 'Uncategorized'}",
            description=f"${spending_data['spent']:.2f} of ${amount:.2f} (${percent_used:.0f}% used)",
            budget_id=budget_id,
            alert_metadata={
                "budget_id": budget_id,
                "category_id": budget.category_id,
                "category_name": budget.category.name if budget.category else "Uncategorized",
                "spent": float(spending_data['spent']),
                "limit": float(amount),
                "percent_used": percent_used,
                "period": budget.period.value
            }
        )
        db.add(alert)
        db.commit()
        return alert
    
    return None


def check_all_budget_alerts(db: Session) -> List[Alert]:
    """
    Check all active budgets and generate alerts for any that need them.
    
    Returns list of created alerts.
    """
    active_budgets = db.query(Budget).filter(
        Budget.is_active == True
    ).all()
    
    created_alerts = []
    for budget in active_budgets:
        alert = check_budget_alerts(db, str(budget.id))
        if alert:
            created_alerts.append(alert)
    
    return created_alerts


def get_budget_alert_summary(db: Session, budget_id: str) -> Dict[str, Any]:
    """Get summary of budget alert status, including recent alerts."""
    budget = db.query(Budget).filter(Budget.id == budget_id, Budget.is_active == True).first()
    if not budget:
        return {}
    
    spending_data = get_budget_spending(db, budget)
    
    recent_alerts = db.query(Alert).filter(
        Alert.budget_id == budget_id,
        Alert.created_at >= datetime.now() - timedelta(days=30)
    ).order_by(Alert.created_at.desc()).all()
    
    return {
        "budget_id": budget_id,
        "category_name": budget.category.name if budget.category else "Uncategorized",
        "total_spent": float(spending_data['spent']),
        "budget_limit": float(budget.amount),
        "percent_used": spending_data['percent_used'],
        "period": budget.period.value,
        "recent_alerts": [
            {
                "id": str(alert.id),
                "type": alert.type.value,
                "severity": alert.severity.value,
                "title": alert.title,
                "created_at": alert.created_at.isoformat(),
                "is_read": alert.is_read,
                "is_dismissed": alert.is_dismissed
            }
            for alert in recent_alerts
        ]
    }
