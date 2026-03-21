"""
Main API router.
"""

from fastapi import APIRouter
from app.api import (
    accounts,
    categories,
    imports,
    transactions,
    settings,
    dashboard,
    alerts,
    privacy,
    budgets,
    recurring,
    v1,
    coach,
    rules,
    insights,
)

api_router = APIRouter()

api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(budgets.router, prefix="/budgets", tags=["budgets"])
api_router.include_router(imports.router)
api_router.include_router(transactions.router)
api_router.include_router(settings.router)
api_router.include_router(dashboard.router)
api_router.include_router(alerts.router)
api_router.include_router(privacy.router)
api_router.include_router(recurring.router)
api_router.include_router(coach.router)
api_router.include_router(rules.router)
api_router.include_router(insights.router)

api_router.include_router(v1.router, tags=["networth"])
