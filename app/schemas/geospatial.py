"""
Pydantic schemas for geospatial data.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class StationLocationResponse(BaseModel):
    """Schema for station location response."""
    station_id: str
    name: str
    latitude: float
    longitude: float
    elevation: Optional[float] = None
    is_active: bool
    aquifer_type: Optional[str] = None
    well_depth: Optional[float] = None
    distance_km: Optional[float] = None


class MapLayerResponse(BaseModel):
    """Schema for map layer response."""
    id: str
    name: str
    type: str  # point, polygon, line
    description: str
    visible: bool
    style: Dict[str, Any]


class GeospatialQueryResponse(BaseModel):
    """Schema for geospatial query response."""
    query_location: Dict[str, Any]
    stations: List[StationLocationResponse]
    aquifer_info: Optional[Dict[str, Any]] = None
    weather_info: Optional[Dict[str, Any]] = None


class DistanceResponse(BaseModel):
    """Schema for distance calculation response."""
    point1: Dict[str, float]
    point2: Dict[str, float]
    distance_km: float
    distance_miles: float


class ElevationProfilePoint(BaseModel):
    """Schema for elevation profile point."""
    latitude: float
    longitude: float
    elevation: float
    distance_km: float


class ElevationProfileResponse(BaseModel):
    """Schema for elevation profile response."""
    start_point: Dict[str, float]
    end_point: Dict[str, float]
    profile_points: List[ElevationProfilePoint]
    total_distance_km: float


class BoundingBoxResponse(BaseModel):
    """Schema for bounding box response."""
    bounds: Optional[Dict[str, float]] = None
    center: Optional[Dict[str, float]] = None
    station_count: int
