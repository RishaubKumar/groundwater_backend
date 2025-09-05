"""
Database configuration and session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from influxdb_client import InfluxDBClient
from redis import Redis
from app.core.config import settings

# PostgreSQL Database
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# InfluxDB Client
influx_client = InfluxDBClient(
    url=settings.INFLUXDB_URL,
    token=settings.INFLUXDB_TOKEN,
    org=settings.INFLUXDB_ORG
)

# Redis Client
redis_client = Redis.from_url(settings.REDIS_URL)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_influx_client():
    """Get InfluxDB client."""
    return influx_client


def get_redis_client():
    """Get Redis client."""
    return redis_client
