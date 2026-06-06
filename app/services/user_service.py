from typing import List
from sqlalchemy.orm import Session
from app.exceptions import AppException
from app.models.user import User
from app.schemas.user import UserCreate

def create_user(db: Session, user_in: UserCreate) -> User:
    """
    Creates a new user, checking for unique email constraints.
    Raises 409 Conflict if the email already exists.
    """
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise AppException(
            status_code=409,
            message="Email conflict",
            detail=f"Email '{user_in.email}' is already registered"
        )
    
    new_user = User(name=user_in.name, email=user_in.email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def get_all_users(db: Session) -> List[User]:
    """
    Retrieves all users registered in the system.
    """
    return db.query(User).all()

def get_user_by_id(db: Session, user_id: int) -> User:
    """
    Retrieves a single user by ID.
    Raises 404 Not Found if user is not present.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppException(
            status_code=404,
            message="User not found",
            detail=f"No user exists with id {user_id}"
        )
    return user
