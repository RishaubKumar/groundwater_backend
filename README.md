# Groundwater Monitoring System Backend

A comprehensive backend system for real-time groundwater monitoring and decision support, built with FastAPI, PostgreSQL, InfluxDB, and modern data processing technologies.

## Features

### Core Functionality
- **Real-time Data Ingestion**: MQTT/Kafka pipelines for DWLR telemetry data
- **Time-series Storage**: InfluxDB for high-frequency sensor data
- **Machine Learning**: Water level forecasting and drought risk assessment
- **Analytics Engine**: Anomaly detection, trend analysis, and recharge estimation
- **RESTful API**: Comprehensive REST endpoints with OpenAPI documentation
- **Authentication**: JWT-based authentication with role-based access control
- **Notifications**: Push notifications, email alerts, and SMS notifications
- **Citizen Science**: Manual data submission and community observations
- **Geospatial Services**: Mapping, GIS integration, and location-based queries

### Data Sources
- Digital Water Level Recorders (DWLRs) via telemetry
- Weather data from OpenWeather API and NASA POWER
- Manual citizen science submissions
- Community observations and reports

### Analytics & ML
- Water level forecasting using Random Forest and neural networks
- Drought risk assessment with multi-factor analysis
- Groundwater recharge estimation
- Anomaly detection for sensor failures and data quality
- Pattern recognition in time-series data

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Mobile Apps   │    │   Web Dashboard │    │  Citizen Portal │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │      FastAPI Backend      │
                    │   (Authentication, API)   │
                    └─────────────┬─────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                        │                         │
┌───────┴────────┐    ┌──────────┴──────────┐    ┌────────┴────────┐
│   PostgreSQL   │    │     InfluxDB        │    │     Redis       │
│  (Metadata)    │    │  (Time-series)      │    │    (Cache)      │
└────────────────┘    └─────────────────────┘    └─────────────────┘
        │                        │                         │
        └────────────────────────┼─────────────────────────┘
                                 │
        ┌────────────────────────┼─────────────────────────┐
        │                        │                         │
┌───────┴────────┐    ┌──────────┴──────────┐    ┌────────┴────────┐
│   MQTT Broker  │    │     Kafka           │    │  External APIs  │
│  (Telemetry)   │    │  (Batch Processing) │    │ (Weather, Maps) │
└────────────────┘    └─────────────────────┘    └─────────────────┘
```

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)
- Git

### Using Docker Compose (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd groundwater_backend
   ```

2. **Configure environment**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

3. **Start the services**
   ```bash
   docker-compose up -d
   ```

4. **Access the API**
   - API Documentation: http://localhost:8000/api/v1/docs
   - Health Check: http://localhost:8000/health
   - Admin Interface: http://localhost:8000

### Local Development

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up databases**
   - PostgreSQL: Create database and user
   - InfluxDB: Set up bucket and organization
   - Redis: Start Redis server

3. **Configure environment**
   ```bash
   cp env.example .env
   # Edit .env with your database URLs and API keys
   ```

4. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

5. **Start the application**
   ```bash
   uvicorn app.main:app --reload
   ```

## API Documentation

### Authentication
All API endpoints (except public ones) require authentication using JWT tokens.

```bash
# Register a new user
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "email": "user@example.com", "password": "password123"}'

# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user&password=password123"
```

### Stations
```bash
# Get all stations
curl -X GET "http://localhost:8000/api/v1/stations/" \
  -H "Authorization: Bearer <token>"

# Get station details
curl -X GET "http://localhost:8000/api/v1/stations/STATION001" \
  -H "Authorization: Bearer <token>"

# Get station sensors
curl -X GET "http://localhost:8000/api/v1/stations/STATION001/sensors" \
  -H "Authorization: Bearer <token>"
```

### Analytics
```bash
# Get water level forecast
curl -X GET "http://localhost:8000/api/v1/analytics/STATION001/forecast?sensor_id=SENSOR001&horizon_days=7" \
  -H "Authorization: Bearer <token>"

# Get drought risk assessment
curl -X GET "http://localhost:8000/api/v1/analytics/STATION001/drought-risk?sensor_id=SENSOR001" \
  -H "Authorization: Bearer <token>"

# Get recharge estimate
curl -X GET "http://localhost:8000/api/v1/analytics/STATION001/recharge?days=30" \
  -H "Authorization: Bearer <token>"
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `INFLUXDB_URL` | InfluxDB server URL | Required |
| `INFLUXDB_TOKEN` | InfluxDB authentication token | Required |
| `REDIS_URL` | Redis connection string | Required |
| `SECRET_KEY` | JWT secret key | Required |
| `MQTT_BROKER` | MQTT broker hostname | localhost |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka servers | localhost:9092 |
| `OPENWEATHER_API_KEY` | OpenWeather API key | Optional |
| `NASA_POWER_API_KEY` | NASA POWER API key | Optional |

### Database Schema

The system uses two main databases:

1. **PostgreSQL**: Stores metadata, user data, and relational data
2. **InfluxDB**: Stores time-series sensor data and analytics results

Key tables in PostgreSQL:
- `station`: Monitoring stations
- `sensor`: Individual sensors
- `user`: System users
- `alert`: System alerts
- `citizensubmission`: Citizen science data

## Data Flow

1. **Data Ingestion**
   - DWLRs send data via MQTT to the telemetry service
   - Weather data is fetched from external APIs
   - Manual submissions are received via REST API

2. **Data Processing**
   - Raw data is validated and cleaned
   - Anomalies are detected using statistical methods
   - Data is stored in InfluxDB for time-series analysis

3. **Analytics**
   - ML models generate forecasts and risk assessments
   - Trend analysis identifies patterns in data
   - Recharge estimation combines multiple data sources

4. **API Response**
   - Processed data is served via REST API
   - Real-time updates via WebSocket (future enhancement)
   - Notifications sent for critical events

## Monitoring and Health Checks

### Health Endpoints
- `GET /health`: Overall system health
- `GET /metrics`: System metrics and performance data

### Logging
- Structured logging with different levels
- Log aggregation for production monitoring
- Error tracking and alerting

### Metrics
- API response times and error rates
- Database connection health
- Message queue status
- ML model performance

## Testing

### Run Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v
```

### Test Categories
- **Unit Tests**: Individual function testing
- **Integration Tests**: API endpoint testing
- **Performance Tests**: Load and stress testing

## Deployment

### Production Considerations

1. **Security**
   - Use HTTPS with valid SSL certificates
   - Implement rate limiting
   - Regular security updates
   - API key rotation

2. **Scalability**
   - Horizontal scaling with load balancers
   - Database connection pooling
   - Caching strategies
   - Message queue clustering

3. **Monitoring**
   - Application performance monitoring
   - Database performance metrics
   - Error tracking and alerting
   - Log aggregation

### Cloud Deployment

The system is designed to be cloud-native and can be deployed on:
- AWS (EC2, RDS, ElastiCache, IoT Core)
- Google Cloud Platform (Compute Engine, Cloud SQL, Memorystore)
- Azure (Virtual Machines, Database, Cache)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation

## Roadmap

### Phase 1 (Current)
- ✅ Core API and data ingestion
- ✅ Basic analytics and ML
- ✅ Authentication and authorization
- ✅ Docker deployment

### Phase 2 (Next)
- 🔄 Real-time WebSocket updates
- 🔄 Advanced ML models
- 🔄 Mobile app integration
- 🔄 Advanced geospatial features

### Phase 3 (Future)
- 📋 AI chatbot integration
- 📋 Gamification features
- 📋 Edge computing support
- 📋 Advanced visualization tools
