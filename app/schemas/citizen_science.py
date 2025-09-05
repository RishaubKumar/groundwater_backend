"""
Pydantic schemas for citizen science data.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class CitizenSubmissionBase(BaseModel):
    """Base citizen submission schema."""
    submission_type: str = Field(..., description="Type of submission")
    station_id: str = Field(..., description="Station ID")
    latitude: Optional[float] = Field(None, description="Latitude")
    longitude: Optional[float] = Field(None, description="Longitude")
    accuracy_meters: Optional[float] = Field(None, description="Location accuracy in meters")
    measurement_value: Optional[float] = Field(None, description="Measurement value")
    measurement_unit: Optional[str] = Field(None, description="Measurement unit")
    measurement_date: datetime = Field(..., description="Measurement date")
    notes: Optional[str] = Field(None, description="Additional notes")
    weather_conditions: Optional[str] = Field(None, description="Weather conditions")
    photos: Optional[List[str]] = Field(default_factory=list, description="Photo URLs")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class CitizenSubmissionCreate(CitizenSubmissionBase):
    """Schema for creating a citizen submission."""
    pass


class CitizenSubmissionResponse(CitizenSubmissionBase):
    """Schema for citizen submission response."""
    id: int
    user_id: int
    is_verified: bool
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    verification_notes: Optional[str] = None
    quality_score: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SubmissionFeedbackBase(BaseModel):
    """Base submission feedback schema."""
    feedback_type: str = Field(..., description="Type of feedback")
    feedback_text: str = Field(..., description="Feedback text")
    is_helpful: Optional[bool] = Field(None, description="Whether feedback is helpful")


class SubmissionFeedbackCreate(SubmissionFeedbackBase):
    """Schema for creating submission feedback."""
    pass


class SubmissionFeedback(SubmissionFeedbackBase):
    """Schema for submission feedback response."""
    id: int
    submission_id: int
    feedback_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CommunityObservationBase(BaseModel):
    """Base community observation schema."""
    observation_type: str = Field(..., description="Type of observation")
    title: str = Field(..., description="Observation title")
    description: str = Field(..., description="Observation description")
    latitude: float = Field(..., description="Latitude")
    longitude: float = Field(..., description="Longitude")
    address: Optional[str] = Field(None, description="Address")
    observation_date: datetime = Field(..., description="Observation date")
    severity: str = Field(..., description="Severity level")
    photos: Optional[List[str]] = Field(default_factory=list, description="Photo URLs")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class CommunityObservationCreate(CommunityObservationBase):
    """Schema for creating a community observation."""
    pass


class CommunityObservationResponse(CommunityObservationBase):
    """Schema for community observation response."""
    id: int
    user_id: int
    is_verified: bool
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ObservationResponseBase(BaseModel):
    """Base observation response schema."""
    response_type: str = Field(..., description="Type of response")
    response_text: str = Field(..., description="Response text")


class ObservationResponseCreate(ObservationResponseBase):
    """Schema for creating an observation response."""
    pass


class ObservationResponse(ObservationResponseBase):
    """Schema for observation response."""
    id: int
    observation_id: int
    responded_by: str
    is_official: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CitizenScienceStats(BaseModel):
    """Schema for citizen science statistics."""
    period_days: int
    submissions: Dict[str, Any]
    observations: Dict[str, Any]
