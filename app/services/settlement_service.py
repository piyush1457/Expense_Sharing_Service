from decimal import Decimal
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.exceptions import AppException
from app.models.group import Group, GroupMember
from app.models.expense import Expense, ExpenseSplit
from app.models.settlement import Settlement
from app.models.user import User
from app.schemas.settlement import SettlementCreate
from app.services.expense_service import get_group_or_raise, validate_user_in_group

def get_outstanding_debt(db: Session, group_id: int, paid_by: int, paid_to: int) -> Decimal:
    """
    Calculates the gross outstanding debt from paid_by (debtor) to paid_to (creditor)
    based on unsettled splits in the group.
    """
    unsettled_splits = db.query(ExpenseSplit).join(Expense).filter(
        Expense.group_id == group_id,
        ExpenseSplit.user_id == paid_by,
        Expense.paid_by == paid_to,
        ExpenseSplit.is_settled == False
    ).all()
    
    return sum(s.amount_owed for s in unsettled_splits)

def create_settlement(db: Session, settlement_in: SettlementCreate) -> Dict[str, Any]:
    """
    Records a settlement in the group and updates corresponding expense splits.
    
    - Validates group exists.
    - Validates payer and receiver are group members.
    - Calculates outstanding debt.
    - Validates settlement amount does not exceed gross outstanding debt.
    - Matches settlement amount against unsettled splits, marking them settled
      and creating remainder splits for partial settlements.
    - Saves settlement record.
    """
    # 1. Validate Group
    get_group_or_raise(db, settlement_in.group_id)
    
    # 2. Validate members
    validate_user_in_group(db, settlement_in.group_id, settlement_in.paid_by, "payer")
    validate_user_in_group(db, settlement_in.group_id, settlement_in.paid_to, "receiver")

    # 3. Get gross outstanding debt
    gross_owed = get_outstanding_debt(
        db,
        settlement_in.group_id,
        settlement_in.paid_by,
        settlement_in.paid_to
    )
    
    if settlement_in.amount > gross_owed:
        raise AppException(
            status_code=400,
            message="Invalid settlement amount",
            detail=(
                f"Settlement amount {settlement_in.amount} exceeds what user {settlement_in.paid_by} "
                f"owes user {settlement_in.paid_to} (outstanding: {gross_owed.quantize(Decimal('0.01'))})"
            )
        )

    # 4. Resolve splits in chronological order (by ID)
    unsettled_splits = db.query(ExpenseSplit).join(Expense).filter(
        Expense.group_id == settlement_in.group_id,
        ExpenseSplit.user_id == settlement_in.paid_by,
        Expense.paid_by == settlement_in.paid_to,
        ExpenseSplit.is_settled == False
    ).order_by(ExpenseSplit.id.asc()).all()

    remaining_settlement = settlement_in.amount

    for split in unsettled_splits:
        if remaining_settlement <= Decimal("0.00"):
            break

        if split.amount_owed <= remaining_settlement:
            # Fully settled
            remaining_settlement -= split.amount_owed
            split.is_settled = True
        else:
            # Partially settled. Mark original split settled, create new split for remainder.
            remainder_amount = split.amount_owed - remaining_settlement
            split.is_settled = True
            
            remainder_split = ExpenseSplit(
                expense_id=split.expense_id,
                user_id=split.user_id,
                amount_owed=remainder_amount,
                is_settled=False,
                created_at=split.created_at  # Keep original timestamp context
            )
            db.add(remainder_split)
            remaining_settlement = Decimal("0.00")

    # 5. Save settlement record
    new_settlement = Settlement(
        group_id=settlement_in.group_id,
        paid_by=settlement_in.paid_by,
        paid_to=settlement_in.paid_to,
        amount=settlement_in.amount,
        note=settlement_in.note
    )
    db.add(new_settlement)
    db.commit()
    db.refresh(new_settlement)

    # Calculate remaining debt
    remaining_debt = gross_owed - settlement_in.amount

    return {
        "id": new_settlement.id,
        "group_id": new_settlement.group_id,
        "paid_by": new_settlement.paid_by,
        "paid_to": new_settlement.paid_to,
        "amount": new_settlement.amount,
        "note": new_settlement.note,
        "created_at": new_settlement.created_at,
        "remaining_debt": remaining_debt.quantize(Decimal("0.01"))
    }

def get_group_settlements(db: Session, group_id: int) -> List[Settlement]:
    """
    Retrieves all settlements for a group.
    """
    get_group_or_raise(db, group_id)
    return db.query(Settlement).filter(Settlement.group_id == group_id).all()

def get_smart_suggestions(db: Session, group_id: int) -> Dict[str, Any]:
    """
    Algorithm: Greedy Minimum Transactions.
    
    1. Calculate the net balance of each user in the group.
    2. Separate into creditors (>0) and debtors (<0).
    3. Greedily match the largest creditor and largest debtor, reducing balances.
    4. Return suggestions.
    """
    # 1. Validate Group
    get_group_or_raise(db, group_id)

    # Get all members of the group
    members = db.query(GroupMember).filter(GroupMember.group_id == group_id).all()
    member_ids = [m.user_id for m in members]

    # Initialize net balances
    net_balances = {uid: Decimal("0.00") for uid in member_ids}

    # Query all unsettled splits in the group
    unsettled_splits = db.query(ExpenseSplit).join(Expense).filter(
        Expense.group_id == group_id,
        ExpenseSplit.is_settled == False
    ).all()

    for split in unsettled_splits:
        debtor = split.user_id
        creditor = split.expense.paid_by
        if debtor == creditor:
            continue
        net_balances[debtor] -= split.amount_owed
        net_balances[creditor] += split.amount_owed

    # Get user names
    users = db.query(User).all()
    user_names = {u.id: u.name for u in users}

    # Separate into creditors and debtors
    creditors = []
    debtors = []

    for uid, net_bal in net_balances.items():
        if net_bal > Decimal("0.00"):
            creditors.append([uid, net_bal])
        elif net_bal < Decimal("0.00"):
            debtors.append([uid, net_bal])

    # Sort to greedily match largest absolute balances first
    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1])  # most negative first

    suggestions = []

    while creditors and debtors:
        creditor = creditors[0]
        debtor = debtors[0]

        cred_id, cred_bal = creditor
        debt_id, debt_bal = debtor
        debt_abs = abs(debt_bal)

        settlement_amt = min(cred_bal, debt_abs).quantize(Decimal("0.01"))

        if settlement_amt > Decimal("0.00"):
            suggestions.append({
                "from": user_names.get(debt_id, f"User {debt_id}"),
                "from_id": debt_id,
                "to": user_names.get(cred_id, f"User {cred_id}"),
                "to_id": cred_id,
                "amount": settlement_amt
            })

        creditor[1] -= settlement_amt
        debtor[1] += settlement_amt

        # Remove from lists if balance hits zero
        if creditor[1].quantize(Decimal("0.01")) <= Decimal("0.00"):
            creditors.pop(0)
        if debtor[1].quantize(Decimal("0.01")) >= Decimal("0.00"):
            debtors.pop(0)

        # Re-sort to maintain greedy priority
        creditors.sort(key=lambda x: x[1], reverse=True)
        debtors.sort(key=lambda x: x[1])

    return {
        "suggestions": suggestions,
        "total_transactions_needed": len(suggestions),
        "message": "Minimum transactions to settle all debts"
    }
