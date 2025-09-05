"""
Tests for station endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from app.models.station import Station, Sensor


def test_get_stations(client: TestClient, auth_headers, db_session):
    """Test getting list of stations."""
    # Create test station
    station = Station(
        name="Test Station",
        station_id="TEST001",
        latitude=12.9716,
        longitude=77.5946,
        elevation=920.0,
        is_active=True
    )
    db_session.add(station)
    db_session.commit()
    
    response = client.get("/api/v1/stations/", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["station_id"] == "TEST001"


def test_get_station(client: TestClient, auth_headers, db_session):
    """Test getting specific station."""
    # Create test station
    station = Station(
        name="Test Station",
        station_id="TEST001",
        latitude=12.9716,
        longitude=77.5946,
        elevation=920.0,
        is_active=True
    )
    db_session.add(station)
    db_session.commit()
    
    response = client.get("/api/v1/stations/TEST001", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["station_id"] == "TEST001"
    assert data["name"] == "Test Station"


def test_get_station_not_found(client: TestClient, auth_headers):
    """Test getting non-existent station."""
    response = client.get("/api/v1/stations/NONEXISTENT", headers=auth_headers)
    assert response.status_code == 404


def test_create_station(client: TestClient, admin_auth_headers):
    """Test creating a new station."""
    station_data = {
        "name": "New Station",
        "station_id": "NEW001",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "elevation": 6.0,
        "aquifer_type": "Alluvial",
        "well_depth": 50.0,
        "description": "Test station for Chennai"
    }
    
    response = client.post("/api/v1/stations/", json=station_data, headers=admin_auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["station_id"] == "NEW001"
    assert data["name"] == "New Station"


def test_create_station_duplicate_id(client: TestClient, admin_auth_headers, db_session):
    """Test creating station with duplicate ID."""
    # Create existing station
    station = Station(
        name="Existing Station",
        station_id="EXIST001",
        latitude=12.9716,
        longitude=77.5946,
        is_active=True
    )
    db_session.add(station)
    db_session.commit()
    
    # Try to create station with same ID
    station_data = {
        "name": "Duplicate Station",
        "station_id": "EXIST001",
        "latitude": 13.0827,
        "longitude": 80.2707
    }
    
    response = client.post("/api/v1/stations/", json=station_data, headers=admin_auth_headers)
    assert response.status_code == 400


def test_get_station_sensors(client: TestClient, auth_headers, db_session):
    """Test getting station sensors."""
    # Create test station and sensor
    station = Station(
        name="Test Station",
        station_id="TEST001",
        latitude=12.9716,
        longitude=77.5946,
        is_active=True
    )
    db_session.add(station)
    db_session.commit()
    
    sensor = Sensor(
        sensor_id="SENSOR001",
        station_id="TEST001",
        sensor_type="water_level",
        manufacturer="Test Corp",
        model="WL-100",
        is_active=True
    )
    db_session.add(sensor)
    db_session.commit()
    
    response = client.get("/api/v1/stations/TEST001/sensors", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["sensor_id"] == "SENSOR001"


def test_get_station_health(client: TestClient, auth_headers, db_session):
    """Test getting station health."""
    # Create test station
    station = Station(
        name="Test Station",
        station_id="TEST001",
        latitude=12.9716,
        longitude=77.5946,
        is_active=True
    )
    db_session.add(station)
    db_session.commit()
    
    response = client.get("/api/v1/stations/TEST001/health", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["station_id"] == "TEST001"
    assert "sensor_health" in data


def test_calibrate_sensor(client: TestClient, auth_headers, db_session):
    """Test sensor calibration."""
    # Create test station and sensor
    station = Station(
        name="Test Station",
        station_id="TEST001",
        latitude=12.9716,
        longitude=77.5946,
        is_active=True
    )
    db_session.add(station)
    
    sensor = Sensor(
        sensor_id="SENSOR001",
        station_id="TEST001",
        sensor_type="water_level",
        is_active=True
    )
    db_session.add(sensor)
    db_session.commit()
    
    response = client.post(
        "/api/v1/stations/TEST001/sensors/SENSOR001/calibrate",
        params={"offset": 0.5, "factor": 1.1},
        headers=auth_headers
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["message"] == "Sensor calibrated successfully"
    assert data["offset"] == 0.5
    assert data["factor"] == 1.1


def test_schedule_maintenance(client: TestClient, auth_headers, db_session):
    """Test scheduling maintenance."""
    # Create test station
    station = Station(
        name="Test Station",
        station_id="TEST001",
        latitude=12.9716,
        longitude=77.5946,
        is_active=True
    )
    db_session.add(station)
    db_session.commit()
    
    response = client.post(
        "/api/v1/stations/TEST001/maintenance",
        params={
            "maintenance_type": "calibration",
            "scheduled_date": "2024-02-01T10:00:00Z",
            "notes": "Routine calibration"
        },
        headers=auth_headers
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["message"] == "Maintenance scheduled successfully"
    assert data["maintenance_type"] == "calibration"
