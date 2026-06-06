from decimal import Decimal
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.exceptions import AppException
from app.models.group import Group, GroupMember
from app.models.expense import Expense, ExpenseSplit
from app.models.user import User
from app.services.expense_service import get_group_or_raise
from app.constants import DEFAULT_CATEGORY

def get_group_analytics(db: Session, group_id: int) -> Dict[str, Any]:
    """
    Calculates detailed analytics for a specific group.
    
    Includes:
    - Total expenses and count.
    - Spending by category.
    - Member breakdown: paid, owes (from splits), and net balance.
    - Largest and average expense details.
    """
    group = get_group_or_raise(db, group_id)
    
    expenses = db.query(Expense).filter(Expense.group_id == group_id).all()
    expense_count = len(expenses)
    
    # Calculate total expenses
    total_expenses = sum(e.amount for e in expenses) if expenses else Decimal("0.00")
    total_expenses = total_expenses.quantize(Decimal("0.01"))
    
    # Calculate average expense
    average_expense = (total_expenses / Decimal(expense_count)) if expense_count > 0 else Decimal("0.00")
    average_expense = average_expense.quantize(Decimal("0.01"))
    
    # Calculate largest expense
    largest_expense = None
    if expenses:
        max_expense = max(expenses, key=lambda e: e.amount)
        largest_expense = {
            "description": max_expense.description,
            "amount": max_expense.amount.quantize(Decimal("0.01"))
        }

    # Group members setup
    members = db.query(GroupMember).filter(GroupMember.group_id == group_id).all()
    user_ids = [m.user_id for m in members]
    
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_names = {u.id: u.name for u in users}
    
    # Initialize member breakdown
    # by_member format: name -> {paid, owes, net}
    by_member = {
        user_names[uid]: {"paid": Decimal("0.00"), "owes": Decimal("0.00"), "net": Decimal("0.00")}
        for uid in user_ids
    }
    
    # Category breakdown initialization
    by_category: Dict[str, Decimal] = {}
    
    for expense in expenses:
        payer_name = user_names.get(expense.paid_by)
        if payer_name in by_member:
            by_member[payer_name]["paid"] += expense.amount
            
        # Category breakdown
        cat = expense.category or DEFAULT_CATEGORY
        by_category[cat] = by_category.get(cat, Decimal("0.00")) + expense.amount

        # Accumulate split owes
        for split in expense.splits:
            split_user_name = user_names.get(split.user_id)
            if split_user_name in by_member:
                by_member[split_user_name]["owes"] += split.amount_owed

    # Compute net balance for each member (paid - owes)
    for name, data in by_member.items():
        data["paid"] = data["paid"].quantize(Decimal("0.01"))
        data["owes"] = data["owes"].quantize(Decimal("0.01"))
        data["net"] = (data["paid"] - data["owes"]).quantize(Decimal("0.01"))
        
    # Format category breakdown amounts
    formatted_category = {k: v.quantize(Decimal("0.01")) for k, v in by_category.items()}

    return {
        "group_id": group.id,
        "group_name": group.name,
        "total_expenses": total_expenses,
        "expense_count": expense_count,
        "by_category": formatted_category,
        "by_member": by_member,
        "largest_expense": largest_expense,
        "average_expense": average_expense
    }

def get_user_analytics(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Calculates detailed spending analytics for a user across all groups.
    
    Computes:
    - Lifetime amount paid.
    - Lifetime amount owed (their share of expenses).
    - Overall net balance.
    - Actual consumption categorized.
    - Group breakdown (paid, owes, net per group).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppException(
            status_code=404,
            message="User not found",
            detail=f"No user exists with id {user_id}"
        )
        
    # Fetch all groups user is a member of
    memberships = db.query(GroupMember).filter(GroupMember.user_id == user_id).all()
    group_ids = [m.group_id for m in memberships]
    
    if not group_ids:
        return {
            "user_id": user.id,
            "user_name": user.name,
            "total_paid": Decimal("0.00"),
            "total_owed": Decimal("0.00"),
            "net_balance": Decimal("0.00"),
            "groups_count": 0,
            "by_category": {},
            "group_breakdown": {}
        }
        
    groups = db.query(Group).filter(Group.id.in_(group_ids)).all()
    group_names = {g.id: g.name for g in groups}

    # Fetch all expenses in these groups
    expenses = db.query(Expense).filter(Expense.group_id.in_(group_ids)).all()
    
    total_paid = Decimal("0.00")
    total_owed = Decimal("0.00")
    by_category: Dict[str, Decimal] = {}
    group_breakdown = {
        name: {"paid": Decimal("0.00"), "owes": Decimal("0.00"), "net": Decimal("0.00")}
        for name in group_names.values()
    }

    for expense in expenses:
        gname = group_names[expense.group_id]
        category = expense.category or DEFAULT_CATEGORY
        
        # User share of this expense
        user_share = Decimal("0.00")
        
        if expense.paid_by == user_id:
            # User paid this expense
            total_paid += expense.amount
            group_breakdown[gname]["paid"] += expense.amount
            
            # User's share of their own paid expense = total - sum of splits of others
            others_split_sum = sum(s.amount_owed for s in expense.splits)
            user_share = expense.amount - others_split_sum
        else:
            # User might be a split participant
            user_split = next((s for s in expense.splits if s.user_id == user_id), None)
            if user_split:
                user_share = user_split.amount_owed
                total_owed += user_share
                group_breakdown[gname]["owes"] += user_share

        # Accumulate personal category consumption
        if user_share > Decimal("0.00"):
            by_category[category] = by_category.get(category, Decimal("0.00")) + user_share

    # Format group breakdown and calculate net per group
    formatted_group_breakdown = {}
    for gname, data in group_breakdown.items():
        paid = data["paid"].quantize(Decimal("0.01"))
        owes = data["owes"].quantize(Decimal("0.01"))
        net = (paid - owes).quantize(Decimal("0.01"))
        formatted_group_breakdown[gname] = {
            "paid": paid,
            "owes": owes,
            "net": net
        }

    formatted_category = {k: v.quantize(Decimal("0.01")) for k, v in by_category.items()}

    return {
        "user_id": user.id,
        "user_name": user.name,
        "total_paid": total_paid.quantize(Decimal("0.01")),
        "total_owed": total_owed.quantize(Decimal("0.01")),
        "net_balance": (total_paid - total_owed).quantize(Decimal("0.01")),
        "groups_count": len(group_ids),
        "by_category": formatted_category,
        "group_breakdown": formatted_group_breakdown
    }
