"""
External API services for weather and rainfall data.
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from app.core.config import settings
from app.core.database import get_influx_client, get_redis_client
from app.services.data_processing import DataProcessor

logger = logging.getLogger(__name__)


class WeatherDataService:
    """Service for fetching weather data from external APIs."""
    
    def __init__(self):
        self.influx_client = get_influx_client()
        self.redis_client = get_redis_client()
        self.data_processor = DataProcessor()
        
    async def fetch_openweather_data(self, lat: float, lon: float, station_id: str) -> Dict[str, Any]:
        """Fetch current weather data from OpenWeather API."""
        if not settings.OPENWEATHER_API_KEY:
            logger.warning("OpenWeather API key not configured")
            return {}
        
        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': settings.OPENWEATHER_API_KEY,
                'units': 'metric'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_openweather_data(data, station_id)
                    else:
                        logger.error(f"OpenWeather API error: {response.status}")
                        return {}
                        
        except Exception as e:
            logger.error(f"Error fetching OpenWeather data: {e}")
            return {}
    
    def _parse_openweather_data(self, data: Dict[str, Any], station_id: str) -> Dict[str, Any]:
        """Parse OpenWeather API response."""
        try:
            main = data.get('main', {})
            weather = data.get('weather', [{}])[0]
            wind = data.get('wind', {})
            
            return {
                'station_id': station_id,
                'timestamp': datetime.now().isoformat(),
                'temperature_c': main.get('temp'),
                'humidity_percent': main.get('humidity'),
                'pressure_hpa': main.get('pressure'),
                'wind_speed_ms': wind.get('speed'),
                'wind_direction_deg': wind.get('deg'),
                'weather_condition': weather.get('description'),
                'cloudiness_percent': data.get('clouds', {}).get('all'),
                'visibility_m': data.get('visibility'),
                'source': 'openweather'
            }
        except Exception as e:
            logger.error(f"Error parsing OpenWeather data: {e}")
            return {}
    
    async def fetch_nasa_power_data(self, lat: float, lon: float, station_id: str, 
                                  start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Fetch historical weather data from NASA POWER API."""
        if not settings.NASA_POWER_API_KEY:
            logger.warning("NASA POWER API key not configured")
            return []
        
        try:
            url = "https://power.larc.nasa.gov/api/temporal/daily/point"
            params = {
                'parameters': 'T2M,PRECTOT,WS2M,RH2M,PS,ALLSKY_SFC_SW_DWN',
                'community': 'RE',
                'longitude': lon,
                'latitude': lat,
                'start': start_date,
                'end': end_date,
                'format': 'JSON'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_nasa_power_data(data, station_id)
                    else:
                        logger.error(f"NASA POWER API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error fetching NASA POWER data: {e}")
            return []
    
    def _parse_nasa_power_data(self, data: Dict[str, Any], station_id: str) -> List[Dict[str, Any]]:
        """Parse NASA POWER API response."""
        try:
            results = []
            properties = data.get('properties', {})
            parameter_data = properties.get('parameter', {})
            
            # Extract daily data
            dates = list(parameter_data.get('T2M', {}).keys())
            
            for date in dates:
                try:
                    date_obj = datetime.strptime(date, '%Y%m%d')
                    
                    result = {
                        'station_id': station_id,
                        'timestamp': date_obj.isoformat(),
                        'temperature_c': parameter_data.get('T2M', {}).get(date),
                        'rainfall_mm': parameter_data.get('PRECTOT', {}).get(date),
                        'wind_speed_ms': parameter_data.get('WS2M', {}).get(date),
                        'humidity_percent': parameter_data.get('RH2M', {}).get(date),
                        'pressure_hpa': parameter_data.get('PS', {}).get(date),
                        'solar_radiation_wm2': parameter_data.get('ALLSKY_SFC_SW_DWN', {}).get(date),
                        'source': 'nasa_power'
                    }
                    
                    # Calculate evapotranspiration using simplified formula
                    if result['temperature_c'] and result['solar_radiation_wm2']:
                        result['evapotranspiration_mm'] = self._calculate_et(
                            result['temperature_c'], 
                            result['solar_radiation_wm2']
                        )
                    
                    results.append(result)
                    
                except ValueError:
                    logger.warning(f"Invalid date format: {date}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Error parsing NASA POWER data: {e}")
            return []
    
    def _calculate_et(self, temp_c: float, solar_rad: float) -> float:
        """Calculate evapotranspiration using simplified Hargreaves equation."""
        try:
            # Convert temperature to Kelvin
            temp_k = temp_c + 273.15
            
            # Simplified ET calculation (mm/day)
            et = 0.0023 * (temp_c + 17.8) * (solar_rad / 1000) ** 0.5
            return max(0, et)
        except:
            return 0.0
    
    async def store_weather_data(self, weather_data: Dict[str, Any]):
        """Store weather data in InfluxDB."""
        try:
            write_api = self.influx_client.write_api()
            
            point = Point("weather_data") \
                .tag("station_id", weather_data['station_id']) \
                .tag("source", weather_data.get('source', 'unknown')) \
                .time(weather_data['timestamp'])
            
            # Add all numeric fields
            for key, value in weather_data.items():
                if key not in ['station_id', 'timestamp', 'source'] and value is not None:
                    if isinstance(value, (int, float)):
                        point.field(key, value)
                    else:
                        point.tag(key, str(value))
            
            write_api.write(bucket=settings.INFLUXDB_BUCKET, record=point)
            logger.debug(f"Stored weather data for station {weather_data['station_id']}")
            
        except Exception as e:
            logger.error(f"Error storing weather data: {e}")
    
    async def fetch_and_store_rainfall_data(self, lat: float, lon: float, station_id: str):
        """Fetch and store rainfall data for a station."""
        try:
            # Fetch current weather data
            weather_data = await self.fetch_openweather_data(lat, lon, station_id)
            if weather_data:
                await self.store_weather_data(weather_data)
            
            # Fetch historical data for the last 30 days
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
            
            historical_data = await self.fetch_nasa_power_data(lat, lon, station_id, start_date, end_date)
            
            for data_point in historical_data:
                await self.store_weather_data(data_point)
            
            logger.info(f"Fetched and stored weather data for station {station_id}")
            
        except Exception as e:
            logger.error(f"Error fetching rainfall data: {e}")


class GeospatialService:
    """Service for geospatial data and mapping."""
    
    def __init__(self):
        self.redis_client = get_redis_client()
    
    async def get_station_location_data(self, station_id: str) -> Optional[Dict[str, Any]]:
        """Get location data for a station."""
        try:
            # This would typically query the database for station location
            # For now, return cached data from Redis
            cache_key = f"station_location:{station_id}"
            data = self.redis_client.hgetall(cache_key)
            
            if data:
                return {k.decode(): v.decode() for k, v in data.items()}
            return None
            
        except Exception as e:
            logger.error(f"Error getting station location data: {e}")
            return None
    
    async def get_nearby_stations(self, lat: float, lon: float, radius_km: float = 10) -> List[Dict[str, Any]]:
        """Get stations within a specified radius."""
        try:
            # This would typically use PostGIS for spatial queries
            # For now, return empty list as placeholder
            return []
            
        except Exception as e:
            logger.error(f"Error getting nearby stations: {e}")
            return []
    
    async def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers."""
        try:
            from math import radians, cos, sin, asin, sqrt
            
            # Convert decimal degrees to radians
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            
            # Haversine formula
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * asin(sqrt(a))
            
            # Radius of earth in kilometers
            r = 6371
            return c * r
            
        except Exception as e:
            logger.error(f"Error calculating distance: {e}")
            return 0.0
