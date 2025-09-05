"""
Pydantic schemas for user-related data.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema."""
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    phone: Optional[str] = None
    language: str = "en"
    timezone: str = "UTC"


class UserCreate(UserBase):
    """Schema for creating a user."""
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    notification_preferences: Optional[Dict[str, Any]] = None


class UserResponse(UserBase):
    """Schema for user response."""
    id: int
    is_active: bool
    is_verified: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """Schema for user login."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str
    token_type: str
    expires_in: int


class PasswordChange(BaseModel):
    """Schema for password change."""
    current_password: str
    new_password: str = Field(..., min_length=8)


class APIKeyResponse(BaseModel):
    """Schema for API key response."""
    api_key: str
    expires_at: Optional[datetime] = None


class UserPreferences(BaseModel):
    """Schema for user preferences."""
    language: str = "en"
    timezone: str = "UTC"
    notification_preferences: Dict[str, Any] = Field(default_factory=dict)
    dashboard_preferences: Dict[str, Any] = Field(default_factory=dict)


class RoleBase(BaseModel):
    """Base role schema."""
    name: str
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)


class RoleCreate(RoleBase):
    """Schema for creating a role."""
    pass


class RoleUpdate(BaseModel):
    """Schema for updating a role."""
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None


class RoleResponse(RoleBase):
    """Schema for role response."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserRoleAssignment(BaseModel):
    """Schema for user role assignment."""
    user_id: int
    role_id: int
    assigned_by: Optional[str] = None
    expires_at: Optional[datetime] = None


class UsagePermitBase(BaseModel):
    """Base usage permit schema."""
    station_id: str
    permit_number: str
    total_allocation_m3: float
    valid_from: datetime
    valid_until: datetime
    max_daily_usage_m3: Optional[float] = None


class UsagePermitCreate(UsagePermitBase):
    """Schema for creating a usage permit."""
    user_id: int


class UsagePermitUpdate(BaseModel):
    """Schema for updating a usage permit."""
    total_allocation_m3: Optional[float] = None
    valid_until: Optional[datetime] = None
    max_daily_usage_m3: Optional[float] = None
    is_active: Optional[bool] = None
    is_suspended: Optional[bool] = None
    suspension_reason: Optional[str] = None


class UsagePermitResponse(UsagePermitBase):
    """Schema for usage permit response."""
    id: int
    user_id: int
    used_allocation_m3: float
    remaining_allocation_m3: float
    last_usage_date: Optional[datetime] = None
    usage_frequency_days: Optional[int] = None
    is_active: bool
    is_suspended: bool
    suspension_reason: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UsageRecordBase(BaseModel):
    """Base usage record schema."""
    station_id: str
    usage_date: datetime
    volume_m3: float
    purpose: Optional[str] = None
    crop_type: Optional[str] = None
    area_irrigated_hectares: Optional[float] = None
    notes: Optional[str] = None


class UsageRecordCreate(UsageRecordBase):
    """Schema for creating a usage record."""
    permit_id: int


class UsageRecordResponse(UsageRecordBase):
    """Schema for usage record response."""
    id: int
    permit_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserProfileResponse(BaseModel):
    """Schema for user profile response."""
    user: UserResponse
    roles: List[RoleResponse]
    usage_permits: List[UsagePermitResponse]
    preferences: UserPreferences
    api_key: Optional[str] = None
    api_key_expires: Optional[datetime] = None
