from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator

class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="The user's name")
    email: EmailStr = Field(..., max_length=255, description="The user's email address")

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name cannot be empty or whitespace only")
        return stripped

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
