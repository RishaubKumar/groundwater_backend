"""
Analytics and forecasting endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.analytics import WaterLevelForecast, DroughtRiskAssessment, RechargeEstimate
from app.services.ml_forecasting import MLForecastingService
from app.schemas.analytics import ForecastResponse, DroughtRiskResponse, RechargeResponse

router = APIRouter()


@router.get("/{station_id}/forecast", response_model=List[ForecastResponse])
async def get_water_level_forecast(
    station_id: str = Path(..., description="Station ID"),
    sensor_id: str = Query(..., description="Sensor ID"),
    horizon_days: int = Query(7, ge=1, le=30, description="Forecast horizon in days"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get water level forecast for a station."""
    ml_service = MLForecastingService()
    
    # Check if model exists, train if not
    model_loaded = await ml_service.load_model(station_id, sensor_id)
    if not model_loaded:
        # Train new model
        training_result = await ml_service.train_water_level_model(station_id, sensor_id)
        if training_result.get('status') != 'success':
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to train model: {training_result.get('message', 'Unknown error')}"
            )
    
    # Generate forecast
    horizon_hours = horizon_days * 24
    predictions = await ml_service.predict_water_level(station_id, sensor_id, horizon_hours)
    
    if not predictions:
        raise HTTPException(status_code=404, detail="No forecast data available")
    
    return predictions


@router.get("/{station_id}/drought-risk", response_model=DroughtRiskResponse)
async def get_drought_risk_assessment(
    station_id: str = Path(..., description="Station ID"),
    sensor_id: str = Query(..., description="Sensor ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get drought risk assessment for a station."""
    ml_service = MLForecastingService()
    
    assessment = await ml_service.assess_drought_risk(station_id, sensor_id)
    
    if not assessment or assessment.get('risk_level') == 'unknown':
        raise HTTPException(status_code=404, detail="Drought risk assessment not available")
    
    return assessment


@router.get("/{station_id}/recharge", response_model=RechargeResponse)
async def get_recharge_estimate(
    station_id: str = Path(..., description="Station ID"),
    days: int = Query(30, ge=7, le=365, description="Period for recharge estimation in days"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get groundwater recharge estimate for a station."""
    ml_service = MLForecastingService()
    
    estimate = await ml_service.estimate_recharge(station_id, days)
    
    if not estimate or estimate.get('method') == 'error':
        raise HTTPException(status_code=404, detail="Recharge estimate not available")
    
    return estimate


@router.get("/{station_id}/trends")
async def get_water_level_trends(
    station_id: str = Path(..., description="Station ID"),
    sensor_id: str = Query(..., description="Sensor ID"),
    period_days: int = Query(30, ge=1, le=365, description="Analysis period in days"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get water level trend analysis for a station."""
    from app.core.database import get_influx_client
    from app.services.data_processing import DataProcessor
    
    influx_client = get_influx_client()
    data_processor = DataProcessor()
    
    # Get historical data
    historical_data = await data_processor._get_historical_data(station_id, sensor_id, period_days)
    
    if not historical_data or len(historical_data) < 10:
        raise HTTPException(status_code=404, detail="Insufficient data for trend analysis")
    
    # Calculate trends
    values = [float(d['value']) for d in historical_data]
    timestamps = [datetime.fromisoformat(d['timestamp'].replace('Z', '+00:00')) for d in historical_data]
    
    trend = data_processor._calculate_trend(values, timestamps)
    
    # Calculate additional statistics
    import numpy as np
    
    stats = {
        'current_level': values[-1],
        'historical_mean': np.mean(values),
        'historical_std': np.std(values),
        'min_level': np.min(values),
        'max_level': np.max(values),
        'level_range': np.max(values) - np.min(values),
        'data_points': len(values),
        'period_days': period_days
    }
    
    return {
        'station_id': station_id,
        'sensor_id': sensor_id,
        'trend': trend,
        'statistics': stats,
        'analysis_date': datetime.now().isoformat()
    }


@router.get("/{station_id}/anomalies")
async def get_anomaly_detection_results(
    station_id: str = Path(..., description="Station ID"),
    sensor_id: Optional[str] = Query(None, description="Sensor ID (optional)"),
    days: int = Query(30, ge=1, le=365, description="Analysis period in days"),
    severity: Optional[str] = Query(None, description="Filter by severity level"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get anomaly detection results for a station."""
    query = db.query(AnomalyDetection).filter(
        AnomalyDetection.station_id == station_id,
        AnomalyDetection.timestamp >= datetime.now() - timedelta(days=days)
    )
    
    if sensor_id:
        query = query.filter(AnomalyDetection.sensor_id == sensor_id)
    
    if severity:
        query = query.filter(AnomalyDetection.severity == severity)
    
    anomalies = query.order_by(AnomalyDetection.timestamp.desc()).all()
    
    return {
        'station_id': station_id,
        'sensor_id': sensor_id,
        'anomalies': [
            {
                'id': anomaly.id,
                'sensor_id': anomaly.sensor_id,
                'timestamp': anomaly.timestamp.isoformat(),
                'anomaly_type': anomaly.anomaly_type,
                'severity': anomaly.severity,
                'anomaly_score': anomaly.anomaly_score,
                'expected_value': anomaly.expected_value,
                'actual_value': anomaly.actual_value,
                'description': anomaly.description,
                'is_resolved': anomaly.is_resolved
            }
            for anomaly in anomalies
        ],
        'total_count': len(anomalies),
        'analysis_period_days': days
    }


@router.post("/{station_id}/train-model")
async def train_forecasting_model(
    station_id: str = Path(..., description="Station ID"),
    sensor_id: str = Query(..., description="Sensor ID"),
    force_retrain: bool = Query(False, description="Force retraining even if model exists"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Train or retrain forecasting model for a station."""
    ml_service = MLForecastingService()
    
    # Check if model already exists
    if not force_retrain:
        model_exists = await ml_service.load_model(station_id, sensor_id)
        if model_exists:
            raise HTTPException(
                status_code=400, 
                detail="Model already exists. Use force_retrain=true to retrain."
            )
    
    # Train model
    result = await ml_service.train_water_level_model(station_id, sensor_id)
    
    if result.get('status') != 'success':
        raise HTTPException(
            status_code=400,
            detail=f"Model training failed: {result.get('message', 'Unknown error')}"
        )
    
    return {
        'message': 'Model trained successfully',
        'station_id': station_id,
        'sensor_id': sensor_id,
        'training_metrics': {
            'mae': result.get('mae'),
            'rmse': result.get('rmse'),
            'training_samples': result.get('training_samples'),
            'test_samples': result.get('test_samples')
        }
    }


@router.get("/{station_id}/forecast-accuracy")
async def get_forecast_accuracy(
    station_id: str = Path(..., description="Station ID"),
    sensor_id: str = Query(..., description="Sensor ID"),
    days: int = Query(7, ge=1, le=30, description="Period for accuracy assessment"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get forecast accuracy metrics for a station."""
    # Get historical forecasts and actual values
    start_date = datetime.now() - timedelta(days=days)
    
    forecasts = db.query(WaterLevelForecast).filter(
        WaterLevelForecast.station_id == station_id,
        WaterLevelForecast.forecast_date >= start_date
    ).order_by(WaterLevelForecast.forecast_date).all()
    
    if not forecasts:
        raise HTTPException(status_code=404, detail="No forecast data available for accuracy assessment")
    
    # Get actual values for comparison
    from app.core.database import get_influx_client
    influx_client = get_influx_client()
    
    actual_values = {}
    for forecast in forecasts:
        # Query actual value at forecast time
        query_api = influx_client.query_api()
        query = f'''
        from(bucket: "{influx_client.bucket}")
        |> range(start: {forecast.forecast_date.isoformat()}, stop: {(forecast.forecast_date + timedelta(hours=1)).isoformat()})
        |> filter(fn: (r) => r["_measurement"] == "sensor_data")
        |> filter(fn: (r) => r["station_id"] == "{station_id}")
        |> filter(fn: (r) => r["sensor_id"] == "{sensor_id}")
        |> filter(fn: (r) => r["_field"] == "value")
        |> first()
        '''
        
        result = query_api.query(query)
        for table in result:
            for record in table.records:
                actual_values[forecast.forecast_date] = record.get_value()
                break
    
    # Calculate accuracy metrics
    if not actual_values:
        raise HTTPException(status_code=404, detail="No actual data available for comparison")
    
    errors = []
    for forecast in forecasts:
        if forecast.forecast_date in actual_values:
            actual = actual_values[forecast.forecast_date]
            predicted = forecast.predicted_level
            error = abs(actual - predicted)
            errors.append(error)
    
    if not errors:
        raise HTTPException(status_code=404, detail="No matching actual data found")
    
    import numpy as np
    
    accuracy_metrics = {
        'mean_absolute_error': np.mean(errors),
        'root_mean_square_error': np.sqrt(np.mean([e**2 for e in errors])),
        'max_error': np.max(errors),
        'min_error': np.min(errors),
        'forecast_count': len(forecasts),
        'actual_count': len(actual_values),
        'assessment_period_days': days
    }
    
    return {
        'station_id': station_id,
        'sensor_id': sensor_id,
        'accuracy_metrics': accuracy_metrics,
        'assessment_date': datetime.now().isoformat()
    }
