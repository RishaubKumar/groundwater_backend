"""
User management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.api.dependencies import get_current_active_user, get_current_superuser
from app.models.user import User, Role, UserRole, UsagePermit, UsageRecord
from app.schemas.user import (
    UserResponse, UserUpdate, RoleResponse, RoleCreate, 
    UsagePermitResponse, UsagePermitCreate, UsageRecordResponse, UsageRecordCreate
)

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user's profile."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_my_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile."""
    update_data = user_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """Get list of users (admin only)."""
    query = db.query(User)
    
    if active_only:
        query = query.filter(User.is_active == True)
    
    users = query.offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int = Path(..., description="User ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """Get specific user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int = Path(..., description="User ID"),
    user_update: UserUpdate = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """Update user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/{user_id}")
async def deactivate_user(
    user_id: int = Path(..., description="User ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """Deactivate user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = False
    db.commit()
    
    return {"message": "User deactivated successfully"}


@router.get("/{user_id}/usage-permits", response_model=List[UsagePermitResponse])
async def get_user_usage_permits(
    user_id: int = Path(..., description="User ID"),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user's usage permits."""
    # Users can only view their own permits unless they're admin
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    query = db.query(UsagePermit).filter(UsagePermit.user_id == user_id)
    
    if active_only:
        query = query.filter(UsagePermit.is_active == True)
    
    permits = query.all()
    return permits


@router.post("/{user_id}/usage-permits", response_model=UsagePermitResponse)
async def create_usage_permit(
    user_id: int = Path(..., description="User ID"),
    permit_data: UsagePermitCreate = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """Create usage permit for user (admin only)."""
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if permit number already exists
    existing = db.query(UsagePermit).filter(
        UsagePermit.permit_number == permit_data.permit_number
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Permit number already exists")
    
    # Create permit
    permit = UsagePermit(
        user_id=user_id,
        **permit_data.dict()
    )
    
    db.add(permit)
    db.commit()
    db.refresh(permit)
    
    return permit


@router.get("/{user_id}/usage-records", response_model=List[UsageRecordResponse])
async def get_user_usage_records(
    user_id: int = Path(..., description="User ID"),
    station_id: Optional[str] = Query(None, description="Filter by station ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user's usage records."""
    # Users can only view their own records unless they're admin
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Get user's permits
    permits = db.query(UsagePermit).filter(UsagePermit.user_id == user_id).all()
    permit_ids = [p.id for p in permits]
    
    if not permit_ids:
        return []
    
    # Query usage records
    query = db.query(UsageRecord).filter(UsageRecord.permit_id.in_(permit_ids))
    
    if station_id:
        query = query.filter(UsageRecord.station_id == station_id)
    
    records = query.order_by(UsageRecord.usage_date.desc()).offset(skip).limit(limit).all()
    return records


@router.post("/{user_id}/usage-records", response_model=UsageRecordResponse)
async def create_usage_record(
    user_id: int = Path(..., description="User ID"),
    record_data: UsageRecordCreate = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create usage record."""
    # Verify permit belongs to user
    permit = db.query(UsagePermit).filter(
        UsagePermit.id == record_data.permit_id,
        UsagePermit.user_id == user_id
    ).first()
    
    if not permit:
        raise HTTPException(status_code=404, detail="Permit not found or not owned by user")
    
    # Check if permit is active
    if not permit.is_active:
        raise HTTPException(status_code=400, detail="Permit is not active")
    
    # Check allocation
    if record_data.volume_m3 > permit.remaining_allocation_m3:
        raise HTTPException(
            status_code=400, 
            detail="Usage exceeds remaining allocation"
        )
    
    # Create record
    record = UsageRecord(**record_data.dict())
    
    # Update permit allocation
    permit.used_allocation_m3 += record_data.volume_m3
    permit.remaining_allocation_m3 -= record_data.volume_m3
    permit.last_usage_date = record_data.usage_date
    
    db.add(record)
    db.commit()
    db.refresh(record)
    
    return record


@router.get("/roles/", response_model=List[RoleResponse])
async def get_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """Get all roles (admin only)."""
    roles = db.query(Role).all()
    return roles


@router.post("/roles/", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """Create new role (admin only)."""
    # Check if role already exists
    existing = db.query(Role).filter(Role.name == role_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Role already exists")
    
    role = Role(**role_data.dict())
    db.add(role)
    db.commit()
    db.refresh(role)
    
    return role
