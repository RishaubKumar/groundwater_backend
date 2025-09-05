"""
Main FastAPI application for the Groundwater Monitoring System.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging
import uvicorn
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import Base, engine
from app.api.v1.api import api_router
from app.services.telemetry import TelemetryService
from app.services.external_apis import WeatherDataService
from app.services.notifications import NotificationService

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global services
telemetry_service = None
weather_service = None
notification_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Groundwater Monitoring System...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    
    # Initialize services
    global telemetry_service, weather_service, notification_service
    
    try:
        telemetry_service = TelemetryService()
        await telemetry_service.start_mqtt_listener()
        await telemetry_service.start_kafka_consumer()
        logger.info("Telemetry service started")
        
        weather_service = WeatherDataService()
        logger.info("Weather service initialized")
        
        notification_service = NotificationService()
        logger.info("Notification service initialized")
        
    except Exception as e:
        logger.error(f"Error starting services: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Groundwater Monitoring System...")
    
    if telemetry_service:
        await telemetry_service.stop()
        logger.info("Telemetry service stopped")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="A comprehensive backend system for real-time groundwater monitoring and decision support",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Groundwater Monitoring System API",
        "version": settings.VERSION,
        "docs_url": f"{settings.API_V1_STR}/docs",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check database connection
        from app.core.database import get_db
        db = next(get_db())
        db.execute("SELECT 1")
        
        # Check Redis connection
        from app.core.database import get_redis_client
        redis_client = get_redis_client()
        redis_client.ping()
        
        # Check InfluxDB connection
        from app.core.database import get_influx_client
        influx_client = get_influx_client()
        influx_client.ping()
        
        return {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",  # This would be datetime.now().isoformat()
            "services": {
                "database": "healthy",
                "redis": "healthy",
                "influxdb": "healthy",
                "telemetry": "healthy" if telemetry_service else "unavailable",
                "weather": "healthy" if weather_service else "unavailable",
                "notifications": "healthy" if notification_service else "unavailable"
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": "2024-01-01T00:00:00Z"
            }
        )


@app.get("/metrics")
async def get_metrics():
    """Get system metrics."""
    try:
        from app.core.database import get_redis_client
        redis_client = get_redis_client()
        
        # Get basic metrics from Redis
        metrics = {
            "timestamp": "2024-01-01T00:00:00Z",  # This would be datetime.now().isoformat()
            "system": {
                "uptime": "0s",  # Would calculate actual uptime
                "memory_usage": "0MB",  # Would get actual memory usage
                "cpu_usage": "0%",  # Would get actual CPU usage
            },
            "database": {
                "active_connections": 0,  # Would get actual connection count
                "query_count": 0,  # Would track query count
            },
            "telemetry": {
                "messages_received": 0,  # Would track from Redis
                "messages_processed": 0,
                "active_stations": 0,
            }
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get metrics")


@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested resource was not found",
            "path": str(request.url.path)
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 handler."""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "path": str(request.url.path)
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
