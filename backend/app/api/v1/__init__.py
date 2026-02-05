"""
API v1 endpoints package.
"""

from fastapi import APIRouter

router = APIRouter()

from app.api.v1 import networth

router.include_router(networth.router, prefix="/networth", tags=["networth"])
