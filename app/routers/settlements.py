from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.settlement import SettlementCreate, SettlementResponse
from app.services import settlement_service

router = APIRouter(prefix="/settlements", tags=["settlements"])

@router.post("", response_model=SettlementResponse, status_code=status.HTTP_201_CREATED)
def create_settlement(settlement_in: SettlementCreate, db: Session = Depends(get_db)):
    """
    Records a settlement payment between group members.
    Applies the payment to outstanding splits and returns the updated balance.
    """
    return settlement_service.create_settlement(db, settlement_in)
