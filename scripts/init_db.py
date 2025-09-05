#!/usr/bin/env python3
"""
Database initialization script.
"""

import asyncio
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import Base
from app.core.config import settings
from app.models.user import User, Role
from app.models.station import Station, Sensor
from app.core.security import get_password_hash

def create_tables():
    """Create all database tables."""
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")

def create_default_data():
    """Create default data for the system."""
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Create default roles
        admin_role = Role(
            name="admin",
            description="System administrator with full access",
            permissions=["read", "write", "delete", "admin"]
        )
        
        user_role = Role(
            name="user",
            description="Regular user with basic access",
            permissions=["read", "write"]
        )
        
        viewer_role = Role(
            name="viewer",
            description="Read-only access",
            permissions=["read"]
        )
        
        db.add(admin_role)
        db.add(user_role)
        db.add(viewer_role)
        
        # Create default admin user
        admin_user = User(
            username="admin",
            email="admin@groundwater.com",
            hashed_password=get_password_hash("admin123"),
            full_name="System Administrator",
            is_active=True,
            is_verified=True,
            is_superuser=True
        )
        
        db.add(admin_user)
        
        # Create sample station
        sample_station = Station(
            name="Sample Monitoring Station",
            station_id="SAMPLE001",
            latitude=12.9716,
            longitude=77.5946,
            elevation=920.0,
            aquifer_type="Alluvial",
            well_depth=50.0,
            casing_diameter=0.15,
            screen_length=10.0,
            installation_date="2024-01-01",
            description="Sample station for testing",
            is_active=True,
            data_interval_minutes=15
        )
        
        db.add(sample_station)
        
        # Create sample sensor
        sample_sensor = Sensor(
            sensor_id="WL001",
            station_id="SAMPLE001",
            sensor_type="water_level",
            manufacturer="AquaSense",
            model="WL-200",
            serial_number="AS001234",
            calibration_date="2024-01-01",
            accuracy=0.01,
            is_active=True,
            min_value=0.0,
            max_value=100.0,
            unit="meters"
        )
        
        db.add(sample_sensor)
        
        db.commit()
        print("Default data created successfully")
        
    except Exception as e:
        print(f"Error creating default data: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    """Main initialization function."""
    print("Initializing Groundwater Monitoring System Database...")
    
    try:
        create_tables()
        create_default_data()
        print("Database initialization completed successfully!")
        print("\nDefault credentials:")
        print("Username: admin")
        print("Password: admin123")
        print("\nPlease change the default password after first login.")
        
    except Exception as e:
        print(f"Database initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
