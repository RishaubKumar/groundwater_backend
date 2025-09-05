"""
Pydantic schemas for analytics and forecasting data.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ForecastResponse(BaseModel):
    """Schema for water level forecast response."""
    timestamp: datetime
    predicted_level: float
    confidence_lower: float
    confidence_upper: float
    horizon_hours: int


class DroughtRiskResponse(BaseModel):
    """Schema for drought risk assessment response."""
    risk_level: str
    risk_score: float
    current_level: float
    historical_average: float
    trend: str
    days_to_drought: int


class RechargeResponse(BaseModel):
    """Schema for recharge estimate response."""
    recharge_mm: float
    method: str
    rainfall_mm: float
    level_change_m: float
    period_days: int


class TrendAnalysisResponse(BaseModel):
    """Schema for trend analysis response."""
    station_id: str
    sensor_id: str
    trend: Dict[str, Any]
    statistics: Dict[str, Any]
    analysis_date: datetime


class AnomalyResponse(BaseModel):
    """Schema for anomaly detection response."""
    id: int
    sensor_id: str
    timestamp: datetime
    anomaly_type: str
    severity: str
    anomaly_score: float
    expected_value: float
    actual_value: float
    description: str
    is_resolved: bool


class AnomalyDetectionResponse(BaseModel):
    """Schema for anomaly detection results response."""
    station_id: str
    sensor_id: Optional[str] = None
    anomalies: List[AnomalyResponse]
    total_count: int
    analysis_period_days: int


class ForecastAccuracyResponse(BaseModel):
    """Schema for forecast accuracy response."""
    station_id: str
    sensor_id: str
    accuracy_metrics: Dict[str, Any]
    assessment_date: datetime


class ModelTrainingResponse(BaseModel):
    """Schema for model training response."""
    message: str
    station_id: str
    sensor_id: str
    training_metrics: Dict[str, Any]


class WaterLevelForecastResponse(BaseModel):
    """Schema for water level forecast database response."""
    id: int
    station_id: str
    forecast_date: datetime
    predicted_level: float
    confidence_interval_lower: Optional[float] = None
    confidence_interval_upper: Optional[float] = None
    model_name: str
    model_version: str
    forecast_horizon_days: float
    input_features: Optional[Dict[str, Any]] = None


class DroughtRiskAssessmentResponse(BaseModel):
    """Schema for drought risk assessment database response."""
    id: int
    station_id: str
    assessment_date: datetime
    risk_level: str
    risk_score: float
    days_to_drought: int
    current_level_m: float
    historical_average_m: float
    trend: str
    contributing_factors: Optional[Dict[str, Any]] = None


class RechargeEstimateResponse(BaseModel):
    """Schema for recharge estimate database response."""
    id: int
    station_id: str
    date: datetime
    recharge_mm: float
    method: str
    rainfall_mm: float
    pumping_mm: float
    evapotranspiration_mm: float
    confidence_score: float


class PatternDetectionResponse(BaseModel):
    """Schema for pattern detection response."""
    station_id: str
    sensor_id: str
    pattern_type: str
    confidence: float
    pattern_data: Dict[str, Any]
    detected_at: datetime


class SensorHealthResponse(BaseModel):
    """Schema for sensor health response."""
    sensor_id: str
    data_availability: float
    value_range: float
    value_std: float
    last_update: Optional[datetime] = None
    health_score: float
    status: str  # healthy, warning, critical


class StationAnalyticsResponse(BaseModel):
    """Schema for comprehensive station analytics response."""
    station_id: str
    analysis_date: datetime
    water_level_trend: Dict[str, Any]
    drought_risk: DroughtRiskResponse
    recharge_estimate: RechargeResponse
    sensor_health: List[SensorHealthResponse]
    recent_anomalies: List[AnomalyResponse]
    forecast_accuracy: Optional[ForecastAccuracyResponse] = None
