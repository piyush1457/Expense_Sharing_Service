from decimal import Decimal
from typing import Dict, Any, Optional, List
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.exceptions import AppException
from app.models.expense import Expense, ExpenseSplit
from app.models.user import User

def get_netted_debts(db: Session, group_id: Optional[int] = None) -> Dict[tuple, Decimal]:
    """
    Core balance netting algorithm.
    
    1. Query all unsettled splits.
    2. Sum up gross debts by (debtor_id, creditor_id).
    3. Net out mutual debts (A owes B X, B owes A Y).
    4. Return {(debtor_id, creditor_id): netted_amount}.
    """
    # 1. Query all unsettled splits
    query = db.query(ExpenseSplit).join(Expense).filter(ExpenseSplit.is_settled == False)
    if group_id is not None:
        query = query.filter(Expense.group_id == group_id)
    splits = query.all()

    # 2. Build map of raw gross debts: {(debtor, creditor): amount}
    raw_debts = {}
    for split in splits:
        debtor = split.user_id
        creditor = split.expense.paid_by
        if debtor == creditor:
            continue
        pair = (debtor, creditor)
        raw_debts[pair] = raw_debts.get(pair, Decimal("0.00")) + split.amount_owed

    # 3. Net out mutual debts
    # Collect all unique user IDs involved
    involved_users = set()
    for debtor_id, creditor_id in raw_debts.keys():
        involved_users.add(debtor_id)
        involved_users.add(creditor_id)

    user_list = list(involved_users)
    netted_debts = {}

    # Check every pair of users and calculate net direction
    for i in range(len(user_list)):
        for j in range(i + 1, len(user_list)):
            u1 = user_list[i]
            u2 = user_list[j]

            owes_1_to_2 = raw_debts.get((u1, u2), Decimal("0.00"))
            owes_2_to_1 = raw_debts.get((u2, u1), Decimal("0.00"))

            if owes_1_to_2 > owes_2_to_1:
                diff = owes_1_to_2 - owes_2_to_1
                if diff > Decimal("0.00"):
                    netted_debts[(u1, u2)] = diff.quantize(Decimal("0.01"))
            elif owes_2_to_1 > owes_1_to_2:
                diff = owes_2_to_1 - owes_1_to_2
                if diff > Decimal("0.00"):
                    netted_debts[(u2, u1)] = diff.quantize(Decimal("0.01"))

    return netted_debts

def get_balances_summary(db: Session, group_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Retrieves the balances structure and summary (total expenses, pending settlements)
    either globally or filtered by group_id.
    """
    # Verify group if group_id is provided
    if group_id is not None:
        group_exists = db.query(User).filter(User.id == group_id).first() # check group
        # Wait, let's query the group table instead of User table for group_id check!
        from app.models.group import Group
        group = db.query(Group).filter(Group.id == group_id).first()
        if not group:
            raise AppException(
                status_code=404,
                message="Group not found",
                detail=f"No group exists with id {group_id}"
            )

    netted_debts = get_netted_debts(db, group_id)

    # Resolve names
    users = db.query(User).all()
    user_names = {u.id: u.name for u in users}

    balances_dict = {}
    total_pending_settlements = Decimal("0.00")

    for (debtor_id, creditor_id), amount in netted_debts.items():
        if amount <= Decimal("0.00"):
            continue
        debtor_name = user_names.get(debtor_id, f"User {debtor_id}")
        creditor_name = user_names.get(creditor_id, f"User {creditor_id}")

        if debtor_name not in balances_dict:
            balances_dict[debtor_name] = {"owes": {}}
        
        balances_dict[debtor_name]["owes"][creditor_name] = amount
        total_pending_settlements += amount

    # Calculate total expenses
    exp_query = db.query(func.sum(Expense.amount))
    if group_id is not None:
        exp_query = exp_query.filter(Expense.group_id == group_id)
    total_expenses = exp_query.scalar() or Decimal("0.00")
    total_expenses = Decimal(total_expenses).quantize(Decimal("0.01"))

    return {
        "balances": balances_dict,
        "summary": {
            "total_expenses": total_expenses,
            "total_pending_settlements": total_pending_settlements.quantize(Decimal("0.01"))
        }
    }

def get_user_balances(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Calculates the exact amount a user owes and is owed across the entire system,
    along with their net balance.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppException(
            status_code=404,
            message="User not found",
            detail=f"No user exists with id {user_id}"
        )

    # Compute global netted debts
    netted_debts = get_netted_debts(db, group_id=None)

    users = db.query(User).all()
    user_names = {u.id: u.name for u in users}

    owes_list = []
    is_owed_list = []
    net_balance = Decimal("0.00")

    for (debtor_id, creditor_id), amount in netted_debts.items():
        if amount <= Decimal("0.00"):
            continue
        if debtor_id == user_id:
            creditor_name = user_names.get(creditor_id, f"User {creditor_id}")
            owes_list.append({"to": creditor_name, "amount": amount})
            net_balance -= amount
        elif creditor_id == user_id:
            debtor_name = user_names.get(debtor_id, f"User {debtor_id}")
            is_owed_list.append({"from": debtor_name, "amount": amount})
            net_balance += amount

    return {
        "user": user.name,
        "owes": owes_list,
        "is_owed": is_owed_list,
        "net_balance": net_balance.quantize(Decimal("0.01"))
    }
