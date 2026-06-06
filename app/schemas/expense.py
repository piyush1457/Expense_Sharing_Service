from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from app.constants import ALLOWED_CATEGORIES, ALLOWED_SPLIT_TYPES, SPLIT_TYPE_CUSTOM, DEFAULT_CATEGORY

class CustomSplitInput(BaseModel):
    user_id: int = Field(..., description="ID of the user who owes money")
    amount: Decimal = Field(..., gt=Decimal("0.00"), decimal_places=2, description="Amount owed by this user")


class ExpenseCreate(BaseModel):
    group_id: int = Field(..., description="ID of the group")
    paid_by: int = Field(..., description="ID of the user who paid")
    amount: Decimal = Field(..., gt=Decimal("0.00"), max_digits=10, decimal_places=2, description="Total expense amount")
    description: str = Field(..., min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=50)
    split_type: str = Field("equal")
    custom_splits: Optional[List[CustomSplitInput]] = None

    @field_validator("split_type")
    @classmethod
    def validate_split_type(cls, value: str) -> str:
        if value not in ALLOWED_SPLIT_TYPES:
            raise ValueError(f"split_type must be one of {ALLOWED_SPLIT_TYPES}")
        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("description cannot be empty or whitespace only")
        return stripped

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not value.strip():
            return DEFAULT_CATEGORY
        cleaned = value.strip().title()
        if cleaned not in ALLOWED_CATEGORIES:
            raise ValueError(f"category must be one of {ALLOWED_CATEGORIES}")
        return cleaned

    @model_validator(mode="after")
    def validate_custom_splits(self):
        if self.split_type == SPLIT_TYPE_CUSTOM:
            if not self.custom_splits:
                raise ValueError("custom_splits is required when split_type is 'custom'")
            total_split_amount = sum(s.amount for s in self.custom_splits)
            if total_split_amount != self.amount:
                raise ValueError(
                    f"Sum of custom splits ({total_split_amount}) must equal total amount ({self.amount})"
                )
        else:
            if self.custom_splits is not None:
                raise ValueError("custom_splits must not be provided when split_type is 'equal'")
        return self


class ExpenseSplitResponse(BaseModel):
    user_id: int
    user_name: str
    amount_owed: Decimal

    class Config:
        from_attributes = True


class ExpenseResponse(BaseModel):
    id: int
    group_id: int
    paid_by: str  # Payer name
    amount: Decimal
    description: str
    category: Optional[str]
    split_type: str
    splits: List[ExpenseSplitResponse]
    created_at: datetime

    class Config:
        from_attributes = True
