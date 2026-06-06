from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator

class SettlementCreate(BaseModel):
    group_id: int = Field(..., description="ID of the group")
    paid_by: int = Field(..., description="ID of the user paying back")
    paid_to: int = Field(..., description="ID of the user receiving money")
    amount: Decimal = Field(..., gt=Decimal("0.00"), max_digits=10, decimal_places=2, description="Settlement amount")
    note: Optional[str] = Field(None, max_length=255, description="Optional note/memo for payment")

    @model_validator(mode="after")
    def validate_different_users(self):
        if self.paid_by == self.paid_to:
            raise ValueError("paid_by and paid_to must be different users")
        return self


class SettlementResponse(BaseModel):
    id: int
    group_id: int
    paid_by: int
    paid_to: int
    amount: Decimal
    note: Optional[str]
    created_at: datetime
    remaining_debt: Decimal = Field(..., description="Remaining amount owed by paid_by to paid_to after this settlement")

    class Config:
        from_attributes = True
