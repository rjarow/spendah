"""API endpoints for alerts management."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.models.alert import Alert, AlertSettings
from app.schemas.alert import (
    AlertResponse,
    AlertsListResponse,
    AlertUpdate,
    UnreadCountResponse,
    AlertSettingsResponse,
    AlertSettingsUpdate,
)
from app.services import alerts_service

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=AlertsListResponse)
def get_alerts(
    is_read: Optional[bool] = Query(None),
    is_dismissed: Optional[bool] = Query(None),
    type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get alerts with optional filters."""
    alerts = alerts_service.get_alerts(
        db,
        is_read=is_read,
        is_dismissed=is_dismissed,
        alert_type=type,
        limit=limit
    )
    unread_count = alerts_service.get_unread_count(db)

    alert_items = [
        AlertResponse(
            id=str(a.id),
            type=a.type,
            severity=a.severity,
            title=a.title,
            description=a.description,
            transaction_id=str(a.transaction_id) if a.transaction_id else None,
            recurring_group_id=str(a.recurring_group_id) if a.recurring_group_id else None,
            metadata=a.alert_metadata,
            is_read=a.is_read,
            is_dismissed=a.is_dismissed,
            action_taken=a.action_taken,
            created_at=a.created_at,
        ) for a in alerts
    ]

    return AlertsListResponse(
        items=alert_items,
        unread_count=unread_count,
        total=len(alerts)
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(db: Session = Depends(get_db)):
    """Get count of unread alerts."""
    count = alerts_service.get_unread_count(db)
    return UnreadCountResponse(count=count)


@router.patch("/{alert_id}", response_model=AlertResponse)
def update_alert(
    alert_id: str,
    update: AlertUpdate,
    db: Session = Depends(get_db)
):
    """Update an alert (mark read, dismiss, record action)."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alert, field, value)

    db.commit()
    db.refresh(alert)

    return AlertResponse(
        id=str(alert.id),
        type=alert.type,
        severity=alert.severity,
        title=alert.title,
        description=alert.description,
        transaction_id=str(alert.transaction_id) if alert.transaction_id else None,
        recurring_group_id=str(alert.recurring_group_id) if alert.recurring_group_id else None,
        metadata=alert.alert_metadata,
        is_read=alert.is_read,
        is_dismissed=alert.is_dismissed,
        action_taken=alert.action_taken,
        created_at=alert.created_at,
    )


@router.post("/mark-all-read")
def mark_all_read(db: Session = Depends(get_db)):
    """Mark all alerts as read."""
    count = alerts_service.mark_all_read(db)
    return {"marked_read": count}


@router.delete("/{alert_id}")
def delete_alert(
    alert_id: str,
    db: Session = Depends(get_db)
):
    """Permanently delete an alert."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    db.delete(alert)
    db.commit()

    return {"deleted": True}


@router.get("/settings", response_model=AlertSettingsResponse)
def get_alert_settings(db: Session = Depends(get_db)):
    """Get alert settings."""
    settings = alerts_service.get_or_create_settings(db)
    return AlertSettingsResponse(
        id=str(settings.id),
        large_purchase_threshold=float(settings.large_purchase_threshold) if settings.large_purchase_threshold else None,
        large_purchase_multiplier=float(settings.large_purchase_multiplier),
        unusual_merchant_threshold=float(settings.unusual_merchant_threshold),
        alerts_enabled=settings.alerts_enabled,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


@router.patch("/settings", response_model=AlertSettingsResponse)
def update_alert_settings(
    update: AlertSettingsUpdate,
    db: Session = Depends(get_db)
):
    """Update alert settings."""
    settings = alerts_service.get_or_create_settings(db)

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)

    settings.updated_at = datetime.now()
    db.commit()
    db.refresh(settings)

    return AlertSettingsResponse(
        id=str(settings.id),
        large_purchase_threshold=float(settings.large_purchase_threshold) if settings.large_purchase_threshold else None,
        large_purchase_multiplier=float(settings.large_purchase_multiplier),
        unusual_merchant_threshold=float(settings.unusual_merchant_threshold),
        alerts_enabled=settings.alerts_enabled,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )
