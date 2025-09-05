"""
Pydantic schemas for notification-related data.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class AlertResponse(BaseModel):
    """Schema for alert response."""
    id: int
    station_id: str
    alert_type: str
    severity: str
    title: str
    message: str
    created_at: datetime
    acknowledged: bool
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class NotificationPreferences(BaseModel):
    """Schema for notification preferences."""
    alert_types: List[str] = Field(default_factory=lambda: ["all"])
    severities: List[str] = Field(default_factory=lambda: ["medium", "high", "critical"])
    stations: List[str] = Field(default_factory=list)
    push_enabled: bool = True
    email_enabled: bool = True
    sms_enabled: bool = False
    language: str = "en"
    timezone: str = "UTC"


class PushNotificationRequest(BaseModel):
    """Schema for push notification request."""
    user_ids: List[int]
    title: str
    body: str
    data: Optional[Dict[str, str]] = None


class BulkNotificationResponse(BaseModel):
    """Schema for bulk notification response."""
    success: int
    failed: int
    total: int


class NotificationStats(BaseModel):
    """Schema for notification statistics."""
    period_days: int
    total_alerts: int
    active_alerts: int
    acknowledged_alerts: int
    severity_breakdown: Dict[str, int]
    type_breakdown: Dict[str, int]
    acknowledgment_rate: float
