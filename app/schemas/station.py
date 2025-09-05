"""
Pydantic schemas for station-related data.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class StationBase(BaseModel):
    """Base station schema."""
    name: str
    station_id: str
    latitude: float
    longitude: float
    elevation: Optional[float] = None
    aquifer_type: Optional[str] = None
    well_depth: Optional[float] = None
    casing_diameter: Optional[float] = None
    screen_length: Optional[float] = None
    installation_date: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class StationCreate(StationBase):
    """Schema for creating a station."""
    pass


class StationUpdate(BaseModel):
    """Schema for updating a station."""
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation: Optional[float] = None
    aquifer_type: Optional[str] = None
    well_depth: Optional[float] = None
    casing_diameter: Optional[float] = None
    screen_length: Optional[float] = None
    installation_date: Optional[str] = None
    is_active: Optional[bool] = None
    data_interval_minutes: Optional[int] = None
    calibration_offset: Optional[float] = None
    calibration_factor: Optional[float] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class StationResponse(StationBase):
    """Schema for station response."""
    id: int
    is_active: bool
    data_interval_minutes: int
    calibration_offset: float
    calibration_factor: float
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SensorBase(BaseModel):
    """Base sensor schema."""
    sensor_id: str
    sensor_type: str
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    calibration_date: Optional[str] = None
    calibration_offset: float = 0.0
    calibration_factor: float = 1.0
    accuracy: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    unit: str = "meters"


class SensorCreate(SensorBase):
    """Schema for creating a sensor."""
    station_id: str


class SensorUpdate(BaseModel):
    """Schema for updating a sensor."""
    sensor_type: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    calibration_date: Optional[str] = None
    calibration_offset: Optional[float] = None
    calibration_factor: Optional[float] = None
    accuracy: Optional[float] = None
    is_active: Optional[bool] = None
    last_maintenance: Optional[str] = None
    next_maintenance: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    unit: Optional[str] = None


class SensorResponse(SensorBase):
    """Schema for sensor response."""
    id: int
    station_id: str
    is_active: bool
    last_maintenance: Optional[str] = None
    next_maintenance: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SensorReadingBase(BaseModel):
    """Base sensor reading schema."""
    sensor_id: str
    timestamp: datetime
    value: float
    unit: str
    quality_flag: str = "good"
    raw_value: Optional[float] = None
    is_anomaly: bool = False
    anomaly_score: Optional[float] = None
    is_interpolated: bool = False


class SensorReadingCreate(SensorReadingBase):
    """Schema for creating a sensor reading."""
    pass


class SensorReadingResponse(SensorReadingBase):
    """Schema for sensor reading response."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StationHealthResponse(BaseModel):
    """Schema for station health response."""
    station_id: str
    is_active: bool
    sensor_health: Dict[str, Dict[str, Any]]
    last_updated: datetime


class StationLocationResponse(BaseModel):
    """Schema for station location response."""
    station_id: str
    name: str
    latitude: float
    longitude: float
    elevation: Optional[float] = None
    is_active: bool


class StationSummaryResponse(BaseModel):
    """Schema for station summary response."""
    station_id: str
    name: str
    latitude: float
    longitude: float
    is_active: bool
    sensor_count: int
    active_sensor_count: int
    last_data_received: Optional[datetime] = None
    current_water_level: Optional[float] = None
    water_level_unit: Optional[str] = None
