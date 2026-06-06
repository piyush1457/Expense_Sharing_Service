from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.expense import ExpenseCreate, ExpenseResponse
from app.services import expense_service

router = APIRouter(prefix="/expenses", tags=["expenses"])

@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(expense_in: ExpenseCreate, db: Session = Depends(get_db)):
    """
    Creates a new expense inside a group and pre-computes split records.
    """
    return expense_service.create_expense(db, expense_in)

@router.get("/{expense_id}", response_model=ExpenseResponse)
def get_expense(expense_id: int, db: Session = Depends(get_db)):
    """
    Retrieves a single expense by ID, along with its split participants.
    """
    return expense_service.get_expense_by_id(db, expense_id)
