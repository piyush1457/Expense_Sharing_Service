from typing import List
from sqlalchemy.orm import Session
from app.exceptions import AppException
from app.models.group import Group, GroupMember
from app.models.user import User
from app.schemas.group import GroupCreate, MemberAdd

def create_group(db: Session, group_in: GroupCreate) -> Group:
    """
    Creates a new group.
    Validates that the creator (created_by) user exists.
    """
    creator = db.query(User).filter(User.id == group_in.created_by).first()
    if not creator:
        raise AppException(
            status_code=400,
            message="Creator not found",
            detail=f"No user exists with id {group_in.created_by} to create the group"
        )
    
    new_group = Group(name=group_in.name, created_by=group_in.created_by)
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    return new_group

def get_all_groups(db: Session) -> List[Group]:
    """
    Retrieves all groups.
    """
    return db.query(Group).all()

def get_group_by_id(db: Session, group_id: int) -> Group:
    """
    Retrieves a group by ID. Raises 404 if not found.
    """
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise AppException(
            status_code=404,
            message="Group not found",
            detail=f"No group exists with id {group_id}"
        )
    return group

def add_group_member(db: Session, group_id: int, member_in: MemberAdd) -> GroupMember:
    """
    Adds a user to a group.
    
    Validates:
    - Group exists.
    - User exists.
    - User is not already a member (raises 409 Conflict).
    """
    # 1. Validate Group
    get_group_by_id(db, group_id)
    
    # 2. Validate User
    user = db.query(User).filter(User.id == member_in.user_id).first()
    if not user:
        raise AppException(
            status_code=404,
            message="User not found",
            detail=f"No user exists with id {member_in.user_id} to add to the group"
        )
        
    # 3. Check for duplicates
    existing_member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == member_in.user_id
    ).first()
    
    if existing_member:
        raise AppException(
            status_code=409,
            message="Duplicate membership",
            detail=f"User {member_in.user_id} ({user.name}) is already a member of group {group_id}"
        )

    new_member = GroupMember(group_id=group_id, user_id=member_in.user_id)
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    return new_member

def get_group_members(db: Session, group_id: int) -> List[User]:
    """
    Retrieves all members of a group with user details.
    """
    get_group_by_id(db, group_id)
    
    # Query joined members
    members = db.query(User).join(GroupMember).filter(GroupMember.group_id == group_id).all()
    return members
