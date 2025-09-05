"""
Station management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.station import Station, Sensor, SensorReading
from app.services.telemetry import TelemetryService
from app.services.external_apis import WeatherDataService
from app.schemas.station import StationResponse, StationCreate, SensorResponse, SensorReadingResponse

router = APIRouter()


@router.get("/", response_model=List[StationResponse])
async def get_stations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get list of monitoring stations."""
    query = db.query(Station)
    
    if active_only:
        query = query.filter(Station.is_active == True)
    
    stations = query.offset(skip).limit(limit).all()
    return stations


@router.get("/{station_id}", response_model=StationResponse)
async def get_station(
    station_id: str = Path(..., description="Station ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get specific station details."""
    station = db.query(Station).filter(Station.station_id == station_id).first()
    
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    
    return station


@router.post("/", response_model=StationResponse)
async def create_station(
    station_data: StationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new monitoring station."""
    # Check if station already exists
    existing = db.query(Station).filter(Station.station_id == station_data.station_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Station ID already exists")
    
    # Create station
    station = Station(**station_data.dict())
    db.add(station)
    db.commit()
    db.refresh(station)
    
    return station


@router.get("/{station_id}/sensors", response_model=List[SensorResponse])
async def get_station_sensors(
    station_id: str = Path(..., description="Station ID"),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get sensors for a specific station."""
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    
    query = db.query(Sensor).filter(Sensor.station_id == station_id)
    
    if active_only:
        query = query.filter(Sensor.is_active == True)
    
    sensors = query.all()
    return sensors


@router.get("/{station_id}/sensors/{sensor_id}/readings", response_model=List[SensorReadingResponse])
async def get_sensor_readings(
    station_id: str = Path(..., description="Station ID"),
    sensor_id: str = Path(..., description="Sensor ID"),
    start_time: Optional[datetime] = Query(None, description="Start time for data range"),
    end_time: Optional[datetime] = Query(None, description="End time for data range"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of readings"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get sensor readings for a specific sensor."""
    # Verify station exists
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    
    # Verify sensor exists
    sensor = db.query(Sensor).filter(
        Sensor.sensor_id == sensor_id,
        Sensor.station_id == station_id
    ).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    
    # Set default time range if not provided
    if not end_time:
        end_time = datetime.now()
    if not start_time:
        start_time = end_time - timedelta(days=7)
    
    # Query readings
    query = db.query(SensorReading).filter(
        SensorReading.sensor_id == sensor_id,
        SensorReading.timestamp >= start_time,
        SensorReading.timestamp <= end_time
    ).order_by(SensorReading.timestamp.desc()).limit(limit)
    
    readings = query.all()
    return readings


@router.get("/{station_id}/latest-data")
async def get_latest_station_data(
    station_id: str = Path(..., description="Station ID"),
    current_user: User = Depends(get_current_active_user)
):
    """Get latest data for all sensors at a station."""
    telemetry_service = TelemetryService()
    latest_data = await telemetry_service.get_latest_data(station_id)
    
    if not latest_data:
        raise HTTPException(status_code=404, detail="No recent data found")
    
    return {
        "station_id": station_id,
        "timestamp": datetime.now().isoformat(),
        "sensors": latest_data
    }


@router.get("/{station_id}/weather")
async def get_station_weather(
    station_id: str = Path(..., description="Station ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get weather data for a station."""
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    
    weather_service = WeatherDataService()
    
    # Fetch current weather data
    weather_data = await weather_service.fetch_openweather_data(
        station.latitude, station.longitude, station_id
    )
    
    return weather_data


@router.post("/{station_id}/sensors/{sensor_id}/calibrate")
async def calibrate_sensor(
    station_id: str = Path(..., description="Station ID"),
    sensor_id: str = Path(..., description="Sensor ID"),
    offset: float = Query(..., description="Calibration offset"),
    factor: float = Query(1.0, description="Calibration factor"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Calibrate a sensor."""
    sensor = db.query(Sensor).filter(
        Sensor.sensor_id == sensor_id,
        Sensor.station_id == station_id
    ).first()
    
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    
    # Update calibration parameters
    sensor.calibration_offset = offset
    sensor.calibration_factor = factor
    sensor.calibration_date = datetime.now().isoformat()
    
    db.commit()
    
    return {
        "message": "Sensor calibrated successfully",
        "sensor_id": sensor_id,
        "offset": offset,
        "factor": factor
    }


@router.get("/{station_id}/health")
async def get_station_health(
    station_id: str = Path(..., description="Station ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get station health status."""
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    
    # Get sensor health data from Redis
    from app.core.database import get_redis_client
    redis_client = get_redis_client()
    
    health_data = {}
    for sensor in station.sensors:
        health_key = f"sensor_health:{station_id}:{sensor.sensor_id}"
        health = redis_client.hgetall(health_key)
        
        if health:
            health_data[sensor.sensor_id] = {
                k.decode(): v.decode() for k, v in health.items()
            }
    
    return {
        "station_id": station_id,
        "is_active": station.is_active,
        "sensor_health": health_data,
        "last_updated": datetime.now().isoformat()
    }


@router.post("/{station_id}/maintenance")
async def schedule_maintenance(
    station_id: str = Path(..., description="Station ID"),
    maintenance_type: str = Query(..., description="Type of maintenance"),
    scheduled_date: datetime = Query(..., description="Scheduled maintenance date"),
    notes: str = Query("", description="Maintenance notes"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Schedule maintenance for a station."""
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    
    # Update sensor maintenance dates
    for sensor in station.sensors:
        if maintenance_type in ['calibration', 'general']:
            sensor.last_maintenance = datetime.now().isoformat()
            sensor.next_maintenance = scheduled_date.isoformat()
    
    db.commit()
    
    return {
        "message": "Maintenance scheduled successfully",
        "station_id": station_id,
        "maintenance_type": maintenance_type,
        "scheduled_date": scheduled_date.isoformat()
    }
