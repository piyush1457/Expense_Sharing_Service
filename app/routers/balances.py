from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import balance_service

router = APIRouter(prefix="/balances", tags=["balances"])

@router.get("")
def get_balances(
    group_id: Optional[int] = Query(None, description="Filter balances for a specific group"),
    db: Session = Depends(get_db)
):
    """
    Returns netted balances. If group_id is provided, filters for that group.
    """
    return balance_service.get_balances_summary(db, group_id)

@router.get("/user/{user_id}")
def get_user_balances(user_id: int, db: Session = Depends(get_db)):
    """
    Returns what a specific user owes, is owed, and their net balance across the entire system.
    """
    return balance_service.get_user_balances(db, user_id)
