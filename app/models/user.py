from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    created_groups = relationship("Group", back_populates="creator", cascade="all, delete-orphan")
    memberships = relationship("GroupMember", back_populates="user", cascade="all, delete-orphan")
    expenses_paid = relationship("Expense", back_populates="payer", cascade="all, delete-orphan")
    expense_splits = relationship("ExpenseSplit", back_populates="user", cascade="all, delete-orphan")
    settlements_paid = relationship(
        "Settlement",
        foreign_keys="[Settlement.paid_by]",
        back_populates="payer",
        cascade="all, delete-orphan"
    )
    settlements_received = relationship(
        "Settlement",
        foreign_keys="[Settlement.paid_to]",
        back_populates="receiver",
        cascade="all, delete-orphan"
    )
