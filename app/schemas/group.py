from datetime import datetime
from pydantic import BaseModel, Field, field_validator

class GroupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name cannot be empty or whitespace only")
        return stripped

class GroupCreate(GroupBase):
    created_by: int = Field(..., description="ID of the user creating the group")

class GroupResponse(GroupBase):
    id: int
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True


class MemberAdd(BaseModel):
    user_id: int = Field(..., description="ID of the user to add to the group")


class MemberResponse(BaseModel):
    message: str
    group_id: int
    user_id: int
