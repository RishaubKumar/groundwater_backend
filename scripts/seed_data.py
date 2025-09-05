#!/usr/bin/env python3
"""
Data seeding script for testing and development.
"""

import asyncio
import random
import sys
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_influx_client
from app.core.config import settings
from app.models.station import Station, Sensor
from app.models.user import User
from app.core.security import get_password_hash

def create_sample_stations(db):
    """Create sample monitoring stations."""
    stations_data = [
        {
            "name": "Bangalore Central Station",
            "station_id": "BLR001",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "elevation": 920.0,
            "aquifer_type": "Alluvial",
            "well_depth": 45.0,
            "casing_diameter": 0.15,
            "screen_length": 8.0,
            "installation_date": "2023-01-15",
            "description": "Central monitoring station in Bangalore"
        },
        {
            "name": "Chennai Coastal Station",
            "station_id": "CHN001",
            "latitude": 13.0827,
            "longitude": 80.2707,
            "elevation": 6.0,
            "aquifer_type": "Coastal Alluvial",
            "well_depth": 35.0,
            "casing_diameter": 0.12,
            "screen_length": 6.0,
            "installation_date": "2023-02-20",
            "description": "Coastal monitoring station in Chennai"
        },
        {
            "name": "Delhi Industrial Station",
            "station_id": "DEL001",
            "latitude": 28.7041,
            "longitude": 77.1025,
            "elevation": 216.0,
            "aquifer_type": "Alluvial",
            "well_depth": 60.0,
            "casing_diameter": 0.18,
            "screen_length": 12.0,
            "installation_date": "2023-03-10",
            "description": "Industrial area monitoring station in Delhi"
        },
        {
            "name": "Mumbai Suburban Station",
            "station_id": "MUM001",
            "latitude": 19.0760,
            "longitude": 72.8777,
            "elevation": 14.0,
            "aquifer_type": "Coastal Alluvial",
            "well_depth": 40.0,
            "casing_diameter": 0.14,
            "screen_length": 7.0,
            "installation_date": "2023-04-05",
            "description": "Suburban monitoring station in Mumbai"
        },
        {
            "name": "Hyderabad Rural Station",
            "station_id": "HYD001",
            "latitude": 17.3850,
            "longitude": 78.4867,
            "elevation": 542.0,
            "aquifer_type": "Hard Rock",
            "well_depth": 80.0,
            "casing_diameter": 0.20,
            "screen_length": 15.0,
            "installation_date": "2023-05-12",
            "description": "Rural monitoring station in Hyderabad"
        }
    ]
    
    for station_data in stations_data:
        station = Station(**station_data, is_active=True, data_interval_minutes=15)
        db.add(station)
    
    db.commit()
    print(f"Created {len(stations_data)} sample stations")

def create_sample_sensors(db):
    """Create sample sensors for stations."""
    sensors_data = [
        # Water level sensors
        {"sensor_id": "WL001", "station_id": "BLR001", "sensor_type": "water_level", "manufacturer": "AquaSense", "model": "WL-200", "unit": "meters"},
        {"sensor_id": "WL002", "station_id": "CHN001", "sensor_type": "water_level", "manufacturer": "HydroTech", "model": "HT-150", "unit": "meters"},
        {"sensor_id": "WL003", "station_id": "DEL001", "sensor_type": "water_level", "manufacturer": "AquaSense", "model": "WL-300", "unit": "meters"},
        {"sensor_id": "WL004", "station_id": "MUM001", "sensor_type": "water_level", "manufacturer": "WaterLog", "model": "WL-100", "unit": "meters"},
        {"sensor_id": "WL005", "station_id": "HYD001", "sensor_type": "water_level", "manufacturer": "HydroTech", "model": "HT-250", "unit": "meters"},
        
        # Temperature sensors
        {"sensor_id": "TEMP001", "station_id": "BLR001", "sensor_type": "temperature", "manufacturer": "TempSense", "model": "TS-50", "unit": "celsius"},
        {"sensor_id": "TEMP002", "station_id": "CHN001", "sensor_type": "temperature", "manufacturer": "TempSense", "model": "TS-50", "unit": "celsius"},
        {"sensor_id": "TEMP003", "station_id": "DEL001", "sensor_type": "temperature", "manufacturer": "TempSense", "model": "TS-50", "unit": "celsius"},
        
        # Pressure sensors
        {"sensor_id": "PRESS001", "station_id": "BLR001", "sensor_type": "pressure", "manufacturer": "PressLog", "model": "PL-100", "unit": "bar"},
        {"sensor_id": "PRESS002", "station_id": "DEL001", "sensor_type": "pressure", "manufacturer": "PressLog", "model": "PL-100", "unit": "bar"},
    ]
    
    for sensor_data in sensors_data:
        sensor = Sensor(
            **sensor_data,
            is_active=True,
            accuracy=0.01,
            min_value=0.0,
            max_value=100.0
        )
        db.add(sensor)
    
    db.commit()
    print(f"Created {len(sensors_data)} sample sensors")

def create_sample_users(db):
    """Create sample users."""
    users_data = [
        {
            "username": "researcher1",
            "email": "researcher1@example.com",
            "full_name": "Dr. Sarah Johnson",
            "hashed_password": get_password_hash("password123"),
            "is_active": True,
            "is_verified": True
        },
        {
            "username": "field_engineer",
            "email": "engineer@example.com",
            "full_name": "Mike Chen",
            "hashed_password": get_password_hash("password123"),
            "is_active": True,
            "is_verified": True
        },
        {
            "username": "data_analyst",
            "email": "analyst@example.com",
            "full_name": "Priya Sharma",
            "hashed_password": get_password_hash("password123"),
            "is_active": True,
            "is_verified": True
        }
    ]
    
    for user_data in users_data:
        user = User(**user_data)
        db.add(user)
    
    db.commit()
    print(f"Created {len(users_data)} sample users")

async def generate_sample_sensor_data():
    """Generate sample time-series data for sensors."""
    influx_client = get_influx_client()
    write_api = influx_client.write_api()
    
    # Get all water level sensors
    from app.core.database import get_db
    db = next(get_db())
    sensors = db.query(Sensor).filter(Sensor.sensor_type == "water_level").all()
    
    # Generate data for the last 30 days
    end_time = datetime.now()
    start_time = end_time - timedelta(days=30)
    
    points = []
    current_time = start_time
    
    while current_time <= end_time:
        for sensor in sensors:
            # Generate realistic water level data with some variation
            base_level = 25.0 + (hash(sensor.station_id) % 20)  # Station-specific base level
            seasonal_variation = 2.0 * (1 + 0.5 * (current_time.month - 6) / 6)  # Seasonal effect
            daily_variation = 0.5 * (1 + 0.3 * (current_time.hour - 12) / 12)  # Daily variation
            random_noise = random.uniform(-0.2, 0.2)  # Random noise
            
            water_level = base_level + seasonal_variation + daily_variation + random_noise
            
            point = {
                "measurement": "sensor_data",
                "tags": {
                    "station_id": sensor.station_id,
                    "sensor_id": sensor.sensor_id
                },
                "fields": {
                    "value": round(water_level, 3)
                },
                "time": current_time
            }
            points.append(point)
        
        current_time += timedelta(minutes=15)  # 15-minute intervals
        
        # Write in batches of 1000 points
        if len(points) >= 1000:
            write_api.write(bucket=settings.INFLUXDB_BUCKET, record=points)
            points = []
    
    # Write remaining points
    if points:
        write_api.write(bucket=settings.INFLUXDB_BUCKET, record=points)
    
    print(f"Generated sample sensor data for {len(sensors)} sensors")

def main():
    """Main seeding function."""
    print("Seeding Groundwater Monitoring System with sample data...")
    
    try:
        # Create database engine
        from app.core.database import engine
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Create sample data
        create_sample_stations(db)
        create_sample_sensors(db)
        create_sample_users(db)
        
        # Generate time-series data
        asyncio.run(generate_sample_sensor_data())
        
        print("Sample data seeding completed successfully!")
        print("\nSample user credentials:")
        print("Username: researcher1, Password: password123")
        print("Username: field_engineer, Password: password123")
        print("Username: data_analyst, Password: password123")
        
    except Exception as e:
        print(f"Data seeding failed: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
