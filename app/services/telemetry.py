"""
Telemetry services for DWLR data ingestion via MQTT and Kafka.
"""

import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import paho.mqtt.client as mqtt
from kafka import KafkaProducer, KafkaConsumer
from influxdb_client import InfluxDBClient, Point
from app.core.config import settings
from app.core.database import get_influx_client, get_redis_client
from app.services.data_processing import DataProcessor

logger = logging.getLogger(__name__)


class TelemetryService:
    """Service for handling real-time telemetry data from DWLRs."""
    
    def __init__(self):
        self.influx_client = get_influx_client()
        self.redis_client = get_redis_client()
        self.data_processor = DataProcessor()
        self.mqtt_client = None
        self.kafka_producer = None
        self.kafka_consumer = None
        
    async def start_mqtt_listener(self):
        """Start MQTT client for real-time data ingestion."""
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        
        if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
            self.mqtt_client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
        
        try:
            self.mqtt_client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, 60)
            self.mqtt_client.loop_start()
            logger.info("MQTT client started successfully")
        except Exception as e:
            logger.error(f"Failed to start MQTT client: {e}")
            raise
    
    async def start_kafka_consumer(self):
        """Start Kafka consumer for batch data processing."""
        try:
            self.kafka_consumer = KafkaConsumer(
                'groundwater-data',
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                group_id='groundwater-processor'
            )
            logger.info("Kafka consumer started successfully")
        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {e}")
            raise
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback."""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            # Subscribe to all groundwater data topics
            client.subscribe("groundwater/+/+/data")
            client.subscribe("groundwater/+/+/status")
        else:
            logger.error(f"Failed to connect to MQTT broker: {rc}")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT message callback."""
        try:
            topic_parts = msg.topic.split('/')
            if len(topic_parts) >= 4:
                station_id = topic_parts[1]
                sensor_id = topic_parts[2]
                data_type = topic_parts[3]
                
                payload = json.loads(msg.payload.decode())
                
                if data_type == "data":
                    asyncio.create_task(self._process_sensor_data(station_id, sensor_id, payload))
                elif data_type == "status":
                    asyncio.create_task(self._process_status_data(station_id, sensor_id, payload))
                    
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    async def _process_sensor_data(self, station_id: str, sensor_id: str, data: Dict[str, Any]):
        """Process incoming sensor data."""
        try:
            # Validate data structure
            if not self._validate_sensor_data(data):
                logger.warning(f"Invalid sensor data from {station_id}/{sensor_id}: {data}")
                return
            
            # Add metadata
            data['station_id'] = station_id
            data['sensor_id'] = sensor_id
            data['received_at'] = datetime.now(timezone.utc).isoformat()
            
            # Store in InfluxDB
            await self._store_influx_data(data)
            
            # Process for anomalies
            await self.data_processor.detect_anomalies(station_id, sensor_id, data)
            
            # Cache latest data in Redis
            await self._cache_latest_data(station_id, sensor_id, data)
            
            logger.debug(f"Processed sensor data from {station_id}/{sensor_id}")
            
        except Exception as e:
            logger.error(f"Error processing sensor data: {e}")
    
    async def _process_status_data(self, station_id: str, sensor_id: str, data: Dict[str, Any]):
        """Process station/sensor status data."""
        try:
            # Update sensor status in Redis
            status_key = f"sensor_status:{station_id}:{sensor_id}"
            self.redis_client.hset(status_key, mapping={
                'last_seen': datetime.now(timezone.utc).isoformat(),
                'battery_level': data.get('battery_level', 'unknown'),
                'signal_strength': data.get('signal_strength', 'unknown'),
                'firmware_version': data.get('firmware_version', 'unknown'),
                'status': data.get('status', 'unknown')
            })
            
            # Set expiration for status data (24 hours)
            self.redis_client.expire(status_key, 86400)
            
            logger.debug(f"Updated status for {station_id}/{sensor_id}")
            
        except Exception as e:
            logger.error(f"Error processing status data: {e}")
    
    def _validate_sensor_data(self, data: Dict[str, Any]) -> bool:
        """Validate incoming sensor data."""
        required_fields = ['timestamp', 'value', 'unit']
        return all(field in data for field in required_fields)
    
    async def _store_influx_data(self, data: Dict[str, Any]):
        """Store data in InfluxDB."""
        try:
            write_api = self.influx_client.write_api()
            
            point = Point("sensor_data") \
                .tag("station_id", data['station_id']) \
                .tag("sensor_id", data['sensor_id']) \
                .field("value", float(data['value'])) \
                .time(data['timestamp'])
            
            # Add additional fields if present
            for key, value in data.items():
                if key not in ['station_id', 'sensor_id', 'timestamp', 'value']:
                    if isinstance(value, (int, float)):
                        point.field(key, value)
                    else:
                        point.tag(key, str(value))
            
            write_api.write(bucket=settings.INFLUXDB_BUCKET, record=point)
            
        except Exception as e:
            logger.error(f"Error storing data in InfluxDB: {e}")
            raise
    
    async def _cache_latest_data(self, station_id: str, sensor_id: str, data: Dict[str, Any]):
        """Cache latest data in Redis for quick access."""
        try:
            cache_key = f"latest_data:{station_id}:{sensor_id}"
            self.redis_client.hset(cache_key, mapping={
                'timestamp': data['timestamp'],
                'value': data['value'],
                'unit': data['unit'],
                'received_at': data['received_at']
            })
            
            # Set expiration (1 hour)
            self.redis_client.expire(cache_key, 3600)
            
        except Exception as e:
            logger.error(f"Error caching data: {e}")
    
    async def process_kafka_messages(self):
        """Process messages from Kafka consumer."""
        try:
            for message in self.kafka_consumer:
                data = message.value
                station_id = data.get('station_id')
                sensor_id = data.get('sensor_id')
                
                if station_id and sensor_id:
                    await self._process_sensor_data(station_id, sensor_id, data)
                else:
                    logger.warning(f"Invalid Kafka message: {data}")
                    
        except Exception as e:
            logger.error(f"Error processing Kafka messages: {e}")
    
    async def send_telemetry_command(self, station_id: str, command: str, parameters: Dict[str, Any] = None):
        """Send command to a specific station via MQTT."""
        try:
            if not self.mqtt_client:
                await self.start_mqtt_listener()
            
            topic = f"groundwater/{station_id}/command"
            payload = {
                'command': command,
                'parameters': parameters or {},
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            self.mqtt_client.publish(topic, json.dumps(payload))
            logger.info(f"Sent command {command} to station {station_id}")
            
        except Exception as e:
            logger.error(f"Error sending telemetry command: {e}")
            raise
    
    async def get_latest_data(self, station_id: str, sensor_id: str = None) -> Optional[Dict[str, Any]]:
        """Get latest cached data for a station/sensor."""
        try:
            if sensor_id:
                cache_key = f"latest_data:{station_id}:{sensor_id}"
                data = self.redis_client.hgetall(cache_key)
                return {k.decode(): v.decode() for k, v in data.items()} if data else None
            else:
                # Get latest data for all sensors at station
                pattern = f"latest_data:{station_id}:*"
                keys = self.redis_client.keys(pattern)
                results = {}
                for key in keys:
                    sensor_id = key.decode().split(':')[-1]
                    data = self.redis_client.hgetall(key)
                    results[sensor_id] = {k.decode(): v.decode() for k, v in data.items()}
                return results
                
        except Exception as e:
            logger.error(f"Error getting latest data: {e}")
            return None
    
    async def stop(self):
        """Stop all telemetry services."""
        try:
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            
            if self.kafka_consumer:
                self.kafka_consumer.close()
                
            logger.info("Telemetry services stopped")
            
        except Exception as e:
            logger.error(f"Error stopping telemetry services: {e}")
