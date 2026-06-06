from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.group import GroupCreate, GroupResponse, MemberAdd, MemberResponse
from app.schemas.user import UserResponse
from app.schemas.expense import ExpenseResponse
from app.schemas.settlement import SettlementResponse
from app.services import group_service, expense_service, settlement_service, analytics_service

router = APIRouter(prefix="/groups", tags=["groups"])

@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(group_in: GroupCreate, db: Session = Depends(get_db)):
    """
    Creates a new group.
    """
    return group_service.create_group(db, group_in)

@router.get("", response_model=List[GroupResponse])
def get_groups(db: Session = Depends(get_db)):
    """
    Retrieves all groups.
    """
    return group_service.get_all_groups(db)

@router.get("/{group_id}", response_model=GroupResponse)
def get_group(group_id: int, db: Session = Depends(get_db)):
    """
    Retrieves a single group by ID.
    """
    return group_service.get_group_by_id(db, group_id)

@router.post("/{group_id}/members", response_model=MemberResponse, status_code=status.HTTP_200_OK)
def add_member(group_id: int, member_in: MemberAdd, db: Session = Depends(get_db)):
    """
    Adds a user to a group as a member.
    """
    member = group_service.add_group_member(db, group_id, member_in)
    return {
        "message": "User added successfully",
        "group_id": member.group_id,
        "user_id": member.user_id
    }

@router.get("/{group_id}/members", response_model=List[UserResponse])
def get_members(group_id: int, db: Session = Depends(get_db)):
    """
    Retrieves all members of a specific group.
    """
    return group_service.get_group_members(db, group_id)

@router.get("/{group_id}/expenses", response_model=List[ExpenseResponse])
def get_expenses(group_id: int, db: Session = Depends(get_db)):
    """
    Retrieves all expenses associated with a specific group.
    """
    return expense_service.get_group_expenses(db, group_id)

@router.get("/{group_id}/settlements", response_model=List[SettlementResponse])
def get_settlements(group_id: int, db: Session = Depends(get_db)):
    """
    Retrieves all settlements recorded in a specific group.
    """
    settlements = settlement_service.get_group_settlements(db, group_id)
    # Map Settlements to response structure with remaining_debt set to 0.00 since settlements
    # represent individual transactions.
    from decimal import Decimal
    result = []
    for s in settlements:
        result.append({
            "id": s.id,
            "group_id": s.group_id,
            "paid_by": s.paid_by,
            "paid_to": s.paid_to,
            "amount": s.amount,
            "note": s.note,
            "created_at": s.created_at,
            "remaining_debt": Decimal("0.00")
        })
    return result

@router.get("/{group_id}/settle/suggestions")
def get_settle_suggestions(group_id: int, db: Session = Depends(get_db)):
    """
    Suggests the minimum number of payments (transactions) to settle all debts in a group.
    """
    return settlement_service.get_smart_suggestions(db, group_id)

@router.get("/{group_id}/analytics")
def get_group_spending_analytics(group_id: int, db: Session = Depends(get_db)):
    """
    Retrieves category spending breakdown and member balances for a group.
    """
    return analytics_service.get_group_analytics(db, group_id)
