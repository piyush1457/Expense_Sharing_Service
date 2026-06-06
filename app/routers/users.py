from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import UserCreate, UserResponse
from app.services import user_service, analytics_service

router = APIRouter(prefix="/users", tags=["users"])

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Creates a new user with name and unique email.
    """
    return user_service.create_user(db, user_in)

@router.get("", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db)):
    """
    Retrieves all users.
    """
    return user_service.get_all_users(db)

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """
    Retrieves a single user by ID.
    """
    return user_service.get_user_by_id(db, user_id)

@router.get("/{user_id}/analytics")
def get_user_spending_analytics(user_id: int, db: Session = Depends(get_db)):
    """
    Retrieves user consumption and spending breakdown by category and group.
    """
    return analytics_service.get_user_analytics(db, user_id)
