"""
Geospatial and mapping endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.station import Station
from app.services.external_apis import GeospatialService
from app.schemas.geospatial import (
    StationLocationResponse, MapLayerResponse, 
    GeospatialQueryResponse, DistanceResponse
)

router = APIRouter()


@router.get("/stations", response_model=List[StationLocationResponse])
async def get_station_locations(
    active_only: bool = Query(True, description="Show only active stations"),
    bounds: Optional[str] = Query(None, description="Bounding box (min_lat,min_lon,max_lat,max_lon)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get station locations for mapping."""
    query = db.query(Station)
    
    if active_only:
        query = query.filter(Station.is_active == True)
    
    # Apply bounding box filter if provided
    if bounds:
        try:
            min_lat, min_lon, max_lat, max_lon = map(float, bounds.split(','))
            query = query.filter(
                Station.latitude >= min_lat,
                Station.latitude <= max_lat,
                Station.longitude >= min_lon,
                Station.longitude <= max_lon
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid bounds format")
    
    stations = query.all()
    
    return [
        {
            'station_id': station.station_id,
            'name': station.name,
            'latitude': station.latitude,
            'longitude': station.longitude,
            'elevation': station.elevation,
            'is_active': station.is_active,
            'aquifer_type': station.aquifer_type,
            'well_depth': station.well_depth
        }
        for station in stations
    ]


@router.get("/stations/{station_id}/nearby", response_model=List[StationLocationResponse])
async def get_nearby_stations(
    station_id: str = Path(..., description="Station ID"),
    radius_km: float = Query(10.0, ge=0.1, le=100.0, description="Search radius in kilometers"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of stations to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get stations near a specific station."""
    # Get the reference station
    station = db.query(Station).filter(Station.station_id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    
    geospatial_service = GeospatialService()
    
    # Get all stations
    all_stations = db.query(Station).filter(Station.is_active == True).all()
    
    nearby_stations = []
    for other_station in all_stations:
        if other_station.station_id == station_id:
            continue
        
        distance = await geospatial_service.calculate_distance(
            station.latitude, station.longitude,
            other_station.latitude, other_station.longitude
        )
        
        if distance <= radius_km:
            nearby_stations.append({
                'station_id': other_station.station_id,
                'name': other_station.name,
                'latitude': other_station.latitude,
                'longitude': other_station.longitude,
                'elevation': other_station.elevation,
                'is_active': other_station.is_active,
                'aquifer_type': other_station.aquifer_type,
                'well_depth': other_station.well_depth,
                'distance_km': distance
            })
    
    # Sort by distance and limit results
    nearby_stations.sort(key=lambda x: x['distance_km'])
    return nearby_stations[:limit]


@router.get("/layers", response_model=List[MapLayerResponse])
async def get_map_layers(
    layer_types: Optional[str] = Query(None, description="Comma-separated list of layer types"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get available map layers."""
    available_layers = [
        {
            'id': 'stations',
            'name': 'Monitoring Stations',
            'type': 'point',
            'description': 'Groundwater monitoring stations',
            'visible': True,
            'style': {
                'color': '#007bff',
                'size': 8,
                'opacity': 0.8
            }
        },
        {
            'id': 'aquifer_boundaries',
            'name': 'Aquifer Boundaries',
            'type': 'polygon',
            'description': 'Aquifer boundary polygons',
            'visible': False,
            'style': {
                'color': '#28a745',
                'opacity': 0.3,
                'stroke_color': '#155724',
                'stroke_width': 2
            }
        },
        {
            'id': 'recharge_zones',
            'name': 'Recharge Zones',
            'type': 'polygon',
            'description': 'Groundwater recharge zones',
            'visible': False,
            'style': {
                'color': '#17a2b8',
                'opacity': 0.4,
                'stroke_color': '#0c5460',
                'stroke_width': 1
            }
        },
        {
            'id': 'no_pumping_zones',
            'name': 'No-Pumping Zones',
            'type': 'polygon',
            'description': 'Restricted pumping areas',
            'visible': False,
            'style': {
                'color': '#dc3545',
                'opacity': 0.5,
                'stroke_color': '#721c24',
                'stroke_width': 2
            }
        },
        {
            'id': 'rainfall_contours',
            'name': 'Rainfall Contours',
            'type': 'line',
            'description': 'Rainfall contour lines',
            'visible': False,
            'style': {
                'color': '#6f42c1',
                'width': 2,
                'opacity': 0.7
            }
        }
    ]
    
    if layer_types:
        requested_types = [t.strip() for t in layer_types.split(',')]
        available_layers = [layer for layer in available_layers if layer['id'] in requested_types]
    
    return available_layers


@router.get("/query", response_model=GeospatialQueryResponse)
async def geospatial_query(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    radius_km: float = Query(5.0, ge=0.1, le=50.0, description="Query radius in kilometers"),
    include_stations: bool = Query(True, description="Include nearby stations"),
    include_aquifer_info: bool = Query(True, description="Include aquifer information"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Perform geospatial query at a specific location."""
    geospatial_service = GeospatialService()
    
    result = {
        'query_location': {
            'latitude': lat,
            'longitude': lon,
            'radius_km': radius_km
        },
        'stations': [],
        'aquifer_info': None,
        'weather_info': None
    }
    
    # Find nearby stations
    if include_stations:
        all_stations = db.query(Station).filter(Station.is_active == True).all()
        
        for station in all_stations:
            distance = await geospatial_service.calculate_distance(
                lat, lon, station.latitude, station.longitude
            )
            
            if distance <= radius_km:
                result['stations'].append({
                    'station_id': station.station_id,
                    'name': station.name,
                    'latitude': station.latitude,
                    'longitude': station.longitude,
                    'distance_km': distance,
                    'aquifer_type': station.aquifer_type,
                    'well_depth': station.well_depth
                })
        
        # Sort by distance
        result['stations'].sort(key=lambda x: x['distance_km'])
    
    # Get aquifer information (placeholder)
    if include_aquifer_info:
        result['aquifer_info'] = {
            'aquifer_type': 'Unknown',
            'depth_range': 'Unknown',
            'permeability': 'Unknown',
            'recharge_rate': 'Unknown'
        }
    
    return result


@router.get("/distance", response_model=DistanceResponse)
async def calculate_distance(
    lat1: float = Query(..., description="First point latitude"),
    lon1: float = Query(..., description="First point longitude"),
    lat2: float = Query(..., description="Second point latitude"),
    lon2: float = Query(..., description="Second point longitude"),
    current_user: User = Depends(get_current_active_user)
):
    """Calculate distance between two points."""
    geospatial_service = GeospatialService()
    
    distance = await geospatial_service.calculate_distance(lat1, lon1, lat2, lon2)
    
    return {
        'point1': {'latitude': lat1, 'longitude': lon1},
        'point2': {'latitude': lat2, 'longitude': lon2},
        'distance_km': distance,
        'distance_miles': distance * 0.621371
    }


@router.get("/bounds")
async def get_map_bounds(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get bounding box for all stations."""
    stations = db.query(Station).filter(Station.is_active == True).all()
    
    if not stations:
        return {
            'bounds': None,
            'center': None,
            'station_count': 0
        }
    
    latitudes = [s.latitude for s in stations]
    longitudes = [s.longitude for s in stations]
    
    bounds = {
        'min_latitude': min(latitudes),
        'max_latitude': max(latitudes),
        'min_longitude': min(longitudes),
        'max_longitude': max(longitudes)
    }
    
    center = {
        'latitude': (bounds['min_latitude'] + bounds['max_latitude']) / 2,
        'longitude': (bounds['min_longitude'] + bounds['max_longitude']) / 2
    }
    
    return {
        'bounds': bounds,
        'center': center,
        'station_count': len(stations)
    }


@router.get("/elevation-profile")
async def get_elevation_profile(
    lat1: float = Query(..., description="Start latitude"),
    lon1: float = Query(..., description="Start longitude"),
    lat2: float = Query(..., description="End latitude"),
    lon2: float = Query(..., description="End longitude"),
    points: int = Query(10, ge=2, le=100, description="Number of profile points"),
    current_user: User = Depends(get_current_active_user)
):
    """Get elevation profile between two points."""
    # This would typically use a digital elevation model (DEM)
    # For now, return a placeholder response
    
    import math
    
    # Calculate intermediate points
    profile_points = []
    for i in range(points):
        ratio = i / (points - 1)
        lat = lat1 + (lat2 - lat1) * ratio
        lon = lon1 + (lon2 - lon1) * ratio
        
        # Placeholder elevation calculation (would use DEM in real implementation)
        elevation = 100 + 50 * math.sin(ratio * math.pi)  # Simulated elevation
        
        profile_points.append({
            'latitude': lat,
            'longitude': lon,
            'elevation': elevation,
            'distance_km': ratio * math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2) * 111  # Rough conversion
        })
    
    return {
        'start_point': {'latitude': lat1, 'longitude': lon1},
        'end_point': {'latitude': lat2, 'longitude': lon2},
        'profile_points': profile_points,
        'total_distance_km': profile_points[-1]['distance_km'] if profile_points else 0
    }
