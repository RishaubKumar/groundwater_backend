"""
Data processing and ETL services.
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from app.core.database import get_db, get_influx_client
from app.models.analytics import AnomalyDetection, Alert
from app.models.station import SensorReading
from app.services.ml_forecasting import MLForecastingService

logger = logging.getLogger(__name__)


class DataProcessor:
    """Core data processing service."""
    
    def __init__(self):
        self.influx_client = get_influx_client()
        self.ml_service = MLForecastingService()
    
    async def detect_anomalies(self, station_id: str, sensor_id: str, data: Dict[str, Any]):
        """Detect anomalies in sensor data."""
        try:
            # Get historical data for comparison
            historical_data = await self._get_historical_data(station_id, sensor_id, days=30)
            
            if not historical_data or len(historical_data) < 10:
                logger.warning(f"Insufficient historical data for anomaly detection: {station_id}/{sensor_id}")
                return
            
            # Calculate anomaly score using statistical methods
            current_value = float(data['value'])
            values = [float(d['value']) for d in historical_data]
            
            mean_val = np.mean(values)
            std_val = np.std(values)
            
            if std_val == 0:
                return  # No variation in data
            
            z_score = abs(current_value - mean_val) / std_val
            anomaly_threshold = 3.0  # 3-sigma rule
            
            if z_score > anomaly_threshold:
                await self._create_anomaly_alert(
                    station_id, sensor_id, data, z_score, mean_val, std_val
                )
                
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
    
    async def _get_historical_data(self, station_id: str, sensor_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get historical data for analysis."""
        try:
            query_api = self.influx_client.query_api()
            
            start_time = datetime.now() - timedelta(days=days)
            
            query = f'''
            from(bucket: "{self.influx_client.bucket}")
            |> range(start: {start_time.isoformat()})
            |> filter(fn: (r) => r["_measurement"] == "sensor_data")
            |> filter(fn: (r) => r["station_id"] == "{station_id}")
            |> filter(fn: (r) => r["sensor_id"] == "{sensor_id}")
            |> filter(fn: (r) => r["_field"] == "value")
            |> sort(columns: ["_time"])
            '''
            
            result = query_api.query(query)
            data = []
            
            for table in result:
                for record in table.records:
                    data.append({
                        'timestamp': record.get_time().isoformat(),
                        'value': record.get_value()
                    })
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return []
    
    async def _create_anomaly_alert(self, station_id: str, sensor_id: str, data: Dict[str, Any], 
                                  z_score: float, expected_value: float, std_dev: float):
        """Create an anomaly alert."""
        try:
            db = next(get_db())
            
            anomaly = AnomalyDetection(
                sensor_id=sensor_id,
                station_id=station_id,
                timestamp=datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00')),
                anomaly_type='statistical_outlier',
                severity='high' if z_score > 5 else 'medium',
                anomaly_score=z_score,
                expected_value=expected_value,
                actual_value=float(data['value']),
                description=f"Statistical anomaly detected: z-score={z_score:.2f}"
            )
            
            db.add(anomaly)
            db.commit()
            
            # Create alert
            alert = Alert(
                station_id=station_id,
                alert_type='sensor_anomaly',
                severity=anomaly.severity,
                title=f"Sensor Anomaly Detected - {sensor_id}",
                message=f"Statistical anomaly detected in sensor {sensor_id}. Z-score: {z_score:.2f}",
                metadata={
                    'sensor_id': sensor_id,
                    'anomaly_score': z_score,
                    'expected_value': expected_value,
                    'actual_value': float(data['value'])
                }
            )
            
            db.add(alert)
            db.commit()
            
            logger.warning(f"Created anomaly alert for {station_id}/{sensor_id}: z-score={z_score:.2f}")
            
        except Exception as e:
            logger.error(f"Error creating anomaly alert: {e}")
        finally:
            db.close()
    
    async def process_batch_data(self, data_batch: List[Dict[str, Any]]):
        """Process a batch of sensor data."""
        try:
            # Group data by station and sensor
            grouped_data = {}
            for data in data_batch:
                key = f"{data['station_id']}_{data['sensor_id']}"
                if key not in grouped_data:
                    grouped_data[key] = []
                grouped_data[key].append(data)
            
            # Process each group
            for key, group_data in grouped_data.items():
                station_id, sensor_id = key.split('_')
                await self._process_sensor_group(station_id, sensor_id, group_data)
                
        except Exception as e:
            logger.error(f"Error processing batch data: {e}")
    
    async def _process_sensor_group(self, station_id: str, sensor_id: str, data: List[Dict[str, Any]]):
        """Process data for a specific sensor."""
        try:
            # Sort by timestamp
            data.sort(key=lambda x: x['timestamp'])
            
            # Calculate derived metrics
            values = [float(d['value']) for d in data]
            timestamps = [datetime.fromisoformat(d['timestamp'].replace('Z', '+00:00')) for d in data]
            
            # Calculate trends
            if len(values) > 1:
                trend = self._calculate_trend(values, timestamps)
                
                # Store trend data
                await self._store_trend_data(station_id, sensor_id, trend)
            
            # Detect patterns
            patterns = await self._detect_patterns(values, timestamps)
            if patterns:
                await self._store_pattern_data(station_id, sensor_id, patterns)
            
            # Update sensor health metrics
            await self._update_sensor_health(station_id, sensor_id, data)
            
        except Exception as e:
            logger.error(f"Error processing sensor group: {e}")
    
    def _calculate_trend(self, values: List[float], timestamps: List[datetime]) -> Dict[str, Any]:
        """Calculate trend in data."""
        try:
            if len(values) < 2:
                return {}
            
            # Linear regression
            x = np.arange(len(values))
            y = np.array(values)
            
            # Calculate slope and correlation
            slope = np.polyfit(x, y, 1)[0]
            correlation = np.corrcoef(x, y)[0, 1]
            
            # Calculate rate of change
            time_diff = (timestamps[-1] - timestamps[0]).total_seconds() / 3600  # hours
            rate_of_change = (values[-1] - values[0]) / time_diff if time_diff > 0 else 0
            
            return {
                'slope': slope,
                'correlation': correlation,
                'rate_of_change_per_hour': rate_of_change,
                'trend_direction': 'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'stable'
            }
            
        except Exception as e:
            logger.error(f"Error calculating trend: {e}")
            return {}
    
    async def _detect_patterns(self, values: List[float], timestamps: List[datetime]) -> List[Dict[str, Any]]:
        """Detect patterns in data."""
        try:
            patterns = []
            
            if len(values) < 24:  # Need at least 24 data points
                return patterns
            
            # Detect daily patterns
            daily_pattern = self._detect_daily_pattern(values, timestamps)
            if daily_pattern:
                patterns.append(daily_pattern)
            
            # Detect weekly patterns
            weekly_pattern = self._detect_weekly_pattern(values, timestamps)
            if weekly_pattern:
                patterns.append(weekly_pattern)
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error detecting patterns: {e}")
            return []
    
    def _detect_daily_pattern(self, values: List[float], timestamps: List[datetime]) -> Optional[Dict[str, Any]]:
        """Detect daily patterns in data."""
        try:
            # Group by hour of day
            hourly_data = {}
            for i, timestamp in enumerate(timestamps):
                hour = timestamp.hour
                if hour not in hourly_data:
                    hourly_data[hour] = []
                hourly_data[hour].append(values[i])
            
            # Calculate hourly averages
            hourly_avg = {hour: np.mean(vals) for hour, vals in hourly_data.items()}
            
            if len(hourly_avg) < 12:  # Need data from at least 12 hours
                return None
            
            # Calculate variance in hourly averages
            avg_values = list(hourly_avg.values())
            variance = np.var(avg_values)
            
            # If variance is significant, there's a daily pattern
            if variance > np.var(values) * 0.1:  # 10% of total variance
                return {
                    'pattern_type': 'daily',
                    'hourly_averages': hourly_avg,
                    'variance': variance,
                    'confidence': min(1.0, variance / np.var(values))
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting daily pattern: {e}")
            return None
    
    def _detect_weekly_pattern(self, values: List[float], timestamps: List[datetime]) -> Optional[Dict[str, Any]]:
        """Detect weekly patterns in data."""
        try:
            # Group by day of week
            daily_data = {}
            for i, timestamp in enumerate(timestamps):
                weekday = timestamp.weekday()
                if weekday not in daily_data:
                    daily_data[weekday] = []
                daily_data[weekday].append(values[i])
            
            # Calculate daily averages
            daily_avg = {day: np.mean(vals) for day, vals in daily_data.items()}
            
            if len(daily_avg) < 4:  # Need data from at least 4 days
                return None
            
            # Calculate variance in daily averages
            avg_values = list(daily_avg.values())
            variance = np.var(avg_values)
            
            # If variance is significant, there's a weekly pattern
            if variance > np.var(values) * 0.05:  # 5% of total variance
                return {
                    'pattern_type': 'weekly',
                    'daily_averages': daily_avg,
                    'variance': variance,
                    'confidence': min(1.0, variance / np.var(values))
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting weekly pattern: {e}")
            return None
    
    async def _store_trend_data(self, station_id: str, sensor_id: str, trend: Dict[str, Any]):
        """Store trend data in InfluxDB."""
        try:
            write_api = self.influx_client.write_api()
            
            point = Point("trend_data") \
                .tag("station_id", station_id) \
                .tag("sensor_id", sensor_id) \
                .field("slope", trend.get('slope', 0)) \
                .field("correlation", trend.get('correlation', 0)) \
                .field("rate_of_change_per_hour", trend.get('rate_of_change_per_hour', 0)) \
                .time(datetime.now())
            
            write_api.write(bucket=self.influx_client.bucket, record=point)
            
        except Exception as e:
            logger.error(f"Error storing trend data: {e}")
    
    async def _store_pattern_data(self, station_id: str, sensor_id: str, patterns: List[Dict[str, Any]]):
        """Store pattern data in InfluxDB."""
        try:
            write_api = self.influx_client.write_api()
            
            for pattern in patterns:
                point = Point("pattern_data") \
                    .tag("station_id", station_id) \
                    .tag("sensor_id", sensor_id) \
                    .tag("pattern_type", pattern['pattern_type']) \
                    .field("variance", pattern['variance']) \
                    .field("confidence", pattern['confidence']) \
                    .time(datetime.now())
                
                write_api.write(bucket=self.influx_client.bucket, record=point)
                
        except Exception as e:
            logger.error(f"Error storing pattern data: {e}")
    
    async def _update_sensor_health(self, station_id: str, sensor_id: str, data: List[Dict[str, Any]]):
        """Update sensor health metrics."""
        try:
            # Calculate health metrics
            values = [float(d['value']) for d in data]
            
            health_metrics = {
                'data_availability': len(data) / 24,  # Assuming 24 expected readings per day
                'value_range': max(values) - min(values) if values else 0,
                'value_std': np.std(values) if len(values) > 1 else 0,
                'last_update': data[-1]['timestamp'] if data else None
            }
            
            # Store in Redis for quick access
            redis_client = get_redis_client()
            health_key = f"sensor_health:{station_id}:{sensor_id}"
            redis_client.hset(health_key, mapping={
                'data_availability': health_metrics['data_availability'],
                'value_range': health_metrics['value_range'],
                'value_std': health_metrics['value_std'],
                'last_update': health_metrics['last_update'] or '',
                'updated_at': datetime.now().isoformat()
            })
            
            # Set expiration (24 hours)
            redis_client.expire(health_key, 86400)
            
        except Exception as e:
            logger.error(f"Error updating sensor health: {e}")
    
    async def downsample_data(self, station_id: str, sensor_id: str, 
                            source_interval: str = "1m", target_interval: str = "10m"):
        """Downsample high-frequency data to lower frequency."""
        try:
            query_api = self.influx_client.query_api()
            
            # Calculate time range for downsampling
            end_time = datetime.now()
            start_time = end_time - timedelta(days=7)  # Last 7 days
            
            query = f'''
            from(bucket: "{self.influx_client.bucket}")
            |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
            |> filter(fn: (r) => r["_measurement"] == "sensor_data")
            |> filter(fn: (r) => r["station_id"] == "{station_id}")
            |> filter(fn: (r) => r["sensor_id"] == "{sensor_id}")
            |> filter(fn: (r) => r["_field"] == "value")
            |> aggregateWindow(every: {target_interval}, fn: mean, createEmpty: false)
            |> yield(name: "downsampled")
            '''
            
            result = query_api.query(query)
            
            # Store downsampled data
            write_api = self.influx_client.write_api()
            
            for table in result:
                for record in table.records:
                    point = Point("sensor_data_downsampled") \
                        .tag("station_id", station_id) \
                        .tag("sensor_id", sensor_id) \
                        .tag("interval", target_interval) \
                        .field("value", record.get_value()) \
                        .time(record.get_time())
                    
                    write_api.write(bucket=self.influx_client.bucket, record=point)
            
            logger.info(f"Downsampled data for {station_id}/{sensor_id} to {target_interval}")
            
        except Exception as e:
            logger.error(f"Error downsampling data: {e}")
