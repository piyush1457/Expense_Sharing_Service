from decimal import Decimal
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.exceptions import AppException
from app.models.expense import Expense, ExpenseSplit
from app.models.group import Group, GroupMember
from app.models.user import User
from app.schemas.expense import ExpenseCreate
from app.utils.calculations import distribute_equal_splits
from app.constants import SPLIT_TYPE_EQUAL, SPLIT_TYPE_CUSTOM

def get_group_or_raise(db: Session, group_id: int) -> Group:
    """Helper to get group or raise 404."""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise AppException(
            status_code=404,
            message="Group not found",
            detail=f"No group exists with id {group_id}"
        )
    return group

def validate_group_members_count(db: Session, group_id: int) -> int:
    """Helper to validate group has at least 2 members."""
    count = db.query(GroupMember).filter(GroupMember.group_id == group_id).count()
    if count < 2:
        raise AppException(
            status_code=400,
            message="Invalid group state",
            detail="Group must have at least 2 members to add an expense"
        )
    return count

def validate_user_in_group(db: Session, group_id: int, user_id: int, role_name: str) -> User:
    """Helper to validate that a user is a member of the group."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppException(
            status_code=404,
            message="User not found",
            detail=f"No user exists with id {user_id}"
        )
        
    member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == user_id
    ).first()
    if not member:
        raise AppException(
            status_code=400,
            message="Invalid member check",
            detail=f"User {user_id} ({user.name}) is not a member of group {group_id}"
        )
    return user

def format_expense(expense: Expense) -> Dict[str, Any]:
    """
    Formatically structures the Expense model and its joined relationships 
    into a shape matching the ExpenseResponse schema.
    """
    return {
        "id": expense.id,
        "group_id": expense.group_id,
        "paid_by": expense.payer.name,
        "amount": expense.amount,
        "description": expense.description,
        "category": expense.category,
        "split_type": expense.split_type,
        "splits": [
            {
                "user_id": split.user_id,
                "user_name": split.user.name,
                "amount_owed": split.amount_owed
            }
            for split in expense.splits
        ],
        "created_at": expense.created_at
    }

def create_expense(db: Session, expense_in: ExpenseCreate) -> Dict[str, Any]:
    """
    Creates an expense in the group and pre-computes the splits.
    
    - Validates group exists.
    - Validates group has >= 2 members.
    - Validates payer is a group member.
    - If equal split: distributes total amount among all group members, 
      and stores splits for non-paying members only.
    - If custom split: validates all participants are group members, 
      and stores splits for non-paying members only.
    """
    # 1. Validate Group
    get_group_or_raise(db, expense_in.group_id)
    
    # 2. Validate Group Member Count
    validate_group_members_count(db, expense_in.group_id)
    
    # 3. Validate Payer
    validate_user_in_group(db, expense_in.group_id, expense_in.paid_by, "payer")

    # 4. Perform Split Logic
    splits_to_create: List[ExpenseSplit] = []

    if expense_in.split_type == SPLIT_TYPE_EQUAL:
        # Get all members in the group
        members = db.query(GroupMember).filter(GroupMember.group_id == expense_in.group_id).all()
        member_ids = [m.user_id for m in members]
        
        # Sort member_ids to ensure deterministic rounding allocation
        member_ids.sort()
        
        shares = distribute_equal_splits(expense_in.amount, len(member_ids))
        
        for user_id, share_amount in zip(member_ids, shares):
            # Payer does not owe themselves, so they are excluded from DB splits
            if user_id == expense_in.paid_by:
                continue
            splits_to_create.append(
                ExpenseSplit(
                    user_id=user_id,
                    amount_owed=share_amount,
                    is_settled=False
                )
            )
            
    elif expense_in.split_type == SPLIT_TYPE_CUSTOM:
        # custom_splits is guaranteed by Pydantic validation to sum exactly to expense amount
        for cs in expense_in.custom_splits:
            # Validate split participant is in group
            validate_user_in_group(db, expense_in.group_id, cs.user_id, "split participant")
            
            # Payer does not owe themselves, exclude from DB splits
            if cs.user_id == expense_in.paid_by:
                continue
                
            splits_to_create.append(
                ExpenseSplit(
                    user_id=cs.user_id,
                    amount_owed=cs.amount,
                    is_settled=False
                )
            )

    # 5. Insert records
    new_expense = Expense(
        group_id=expense_in.group_id,
        paid_by=expense_in.paid_by,
        amount=expense_in.amount,
        description=expense_in.description,
        split_type=expense_in.split_type,
        category=expense_in.category
    )
    db.add(new_expense)
    db.flush()  # to generate new_expense.id

    for split in splits_to_create:
        split.expense_id = new_expense.id
        db.add(split)

    db.commit()
    db.refresh(new_expense)
    
    return format_expense(new_expense)

def get_group_expenses(db: Session, group_id: int) -> List[Dict[str, Any]]:
    """
    Retrieves all expenses for a group, formatted with paid_by name.
    """
    get_group_or_raise(db, group_id)
    expenses = db.query(Expense).filter(Expense.group_id == group_id).all()
    return [format_expense(e) for e in expenses]

def get_expense_by_id(db: Session, expense_id: int) -> Dict[str, Any]:
    """
    Retrieves a single expense by ID, formatted with full splits.
    """
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise AppException(
            status_code=404,
            message="Expense not found",
            detail=f"No expense exists with id {expense_id}"
        )
    return format_expense(expense)
