# Groundwater Monitoring System - API Documentation

## Overview

The Groundwater Monitoring System provides a comprehensive REST API for real-time groundwater monitoring, analytics, and decision support. The API is built with FastAPI and provides automatic OpenAPI documentation.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Most endpoints require authentication using JWT tokens. Include the token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

## API Endpoints

### Authentication (`/auth`)

#### Register User
```http
POST /auth/register
Content-Type: application/json

{
  "username": "string",
  "email": "string",
  "password": "string",
  "full_name": "string",
  "phone": "string",
  "language": "string",
  "timezone": "string"
}
```

#### Login
```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=string&password=string
```

#### Get Current User
```http
GET /auth/me
Authorization: Bearer <token>
```

#### Change Password
```http
POST /auth/change-password
Authorization: Bearer <token>
Content-Type: application/json

{
  "current_password": "string",
  "new_password": "string"
}
```

### Stations (`/stations`)

#### Get All Stations
```http
GET /stations/
Authorization: Bearer <token>
Query Parameters:
  - skip: int (default: 0)
  - limit: int (default: 100)
  - active_only: bool (default: true)
```

#### Get Station Details
```http
GET /stations/{station_id}
Authorization: Bearer <token>
```

#### Create Station
```http
POST /stations/
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "string",
  "station_id": "string",
  "latitude": float,
  "longitude": float,
  "elevation": float,
  "aquifer_type": "string",
  "well_depth": float,
  "casing_diameter": float,
  "screen_length": float,
  "installation_date": "string",
  "description": "string"
}
```

#### Get Station Sensors
```http
GET /stations/{station_id}/sensors
Authorization: Bearer <token>
Query Parameters:
  - active_only: bool (default: true)
```

#### Get Sensor Readings
```http
GET /stations/{station_id}/sensors/{sensor_id}/readings
Authorization: Bearer <token>
Query Parameters:
  - start_time: datetime
  - end_time: datetime
  - limit: int (default: 1000)
```

#### Get Latest Station Data
```http
GET /stations/{station_id}/latest-data
Authorization: Bearer <token>
```

#### Get Station Weather
```http
GET /stations/{station_id}/weather
Authorization: Bearer <token>
```

#### Calibrate Sensor
```http
POST /stations/{station_id}/sensors/{sensor_id}/calibrate
Authorization: Bearer <token>
Query Parameters:
  - offset: float
  - factor: float (default: 1.0)
```

#### Get Station Health
```http
GET /stations/{station_id}/health
Authorization: Bearer <token>
```

#### Schedule Maintenance
```http
POST /stations/{station_id}/maintenance
Authorization: Bearer <token>
Query Parameters:
  - maintenance_type: string
  - scheduled_date: datetime
  - notes: string
```

### Analytics (`/analytics`)

#### Get Water Level Forecast
```http
GET /analytics/{station_id}/forecast
Authorization: Bearer <token>
Query Parameters:
  - sensor_id: string
  - horizon_days: int (default: 7, max: 30)
```

#### Get Drought Risk Assessment
```http
GET /analytics/{station_id}/drought-risk
Authorization: Bearer <token>
Query Parameters:
  - sensor_id: string
```

#### Get Recharge Estimate
```http
GET /analytics/{station_id}/recharge
Authorization: Bearer <token>
Query Parameters:
  - days: int (default: 30, max: 365)
```

#### Get Water Level Trends
```http
GET /analytics/{station_id}/trends
Authorization: Bearer <token>
Query Parameters:
  - sensor_id: string
  - period_days: int (default: 30, max: 365)
```

#### Get Anomaly Detection Results
```http
GET /analytics/{station_id}/anomalies
Authorization: Bearer <token>
Query Parameters:
  - sensor_id: string (optional)
  - days: int (default: 30, max: 365)
  - severity: string (optional)
```

#### Train Forecasting Model
```http
POST /analytics/{station_id}/train-model
Authorization: Bearer <token>
Query Parameters:
  - sensor_id: string
  - force_retrain: bool (default: false)
```

#### Get Forecast Accuracy
```http
GET /analytics/{station_id}/forecast-accuracy
Authorization: Bearer <token>
Query Parameters:
  - sensor_id: string
  - days: int (default: 7, max: 30)
```

### Notifications (`/notifications`)

#### Get Alerts
```http
GET /notifications/alerts
Authorization: Bearer <token>
Query Parameters:
  - station_id: string (optional)
  - severity: string (optional)
  - active_only: bool (default: true)
  - skip: int (default: 0)
  - limit: int (default: 100)
```

#### Get Alert Details
```http
GET /notifications/alerts/{alert_id}
Authorization: Bearer <token>
```

#### Acknowledge Alert
```http
POST /notifications/alerts/{alert_id}/acknowledge
Authorization: Bearer <token>
```

#### Resolve Alert
```http
POST /notifications/alerts/{alert_id}/resolve
Authorization: Bearer <token>
Query Parameters:
  - resolution_notes: string (optional)
```

#### Get Notification Preferences
```http
GET /notifications/preferences
Authorization: Bearer <token>
```

#### Update Notification Preferences
```http
PUT /notifications/preferences
Authorization: Bearer <token>
Content-Type: application/json

{
  "alert_types": ["string"],
  "severities": ["string"],
  "stations": ["string"],
  "push_enabled": bool,
  "email_enabled": bool,
  "sms_enabled": bool,
  "language": "string",
  "timezone": "string"
}
```

#### Update FCM Token
```http
POST /notifications/fcm-token
Authorization: Bearer <token>
Query Parameters:
  - token: string
```

#### Send Test Notification
```http
POST /notifications/test-notification
Authorization: Bearer <token>
Query Parameters:
  - title: string
  - body: string
```

#### Get Notification Statistics
```http
GET /notifications/stats
Authorization: Bearer <token>
Query Parameters:
  - days: int (default: 30, max: 365)
```

### Citizen Science (`/citizen-science`)

#### Create Submission
```http
POST /citizen-science/submissions
Authorization: Bearer <token>
Content-Type: application/json

{
  "submission_type": "string",
  "station_id": "string",
  "latitude": float,
  "longitude": float,
  "accuracy_meters": float,
  "measurement_value": float,
  "measurement_unit": "string",
  "measurement_date": "datetime",
  "notes": "string",
  "weather_conditions": "string",
  "photos": ["string"],
  "metadata": {}
}
```

#### Get Submissions
```http
GET /citizen-science/submissions
Authorization: Bearer <token>
Query Parameters:
  - submission_type: string (optional)
  - station_id: string (optional)
  - verified_only: bool (default: false)
  - skip: int (default: 0)
  - limit: int (default: 100)
```

#### Get Submission Details
```http
GET /citizen-science/submissions/{submission_id}
Authorization: Bearer <token>
```

#### Verify Submission
```http
POST /citizen-science/submissions/{submission_id}/verify
Authorization: Bearer <token>
Query Parameters:
  - verification_notes: string (optional)
  - quality_score: float (optional, 0.0-1.0)
```

#### Add Submission Feedback
```http
POST /citizen-science/submissions/{submission_id}/feedback
Authorization: Bearer <token>
Content-Type: application/json

{
  "feedback_type": "string",
  "feedback_text": "string",
  "is_helpful": bool
}
```

#### Create Community Observation
```http
POST /citizen-science/observations
Authorization: Bearer <token>
Content-Type: application/json

{
  "observation_type": "string",
  "title": "string",
  "description": "string",
  "latitude": float,
  "longitude": float,
  "address": "string",
  "observation_date": "datetime",
  "severity": "string",
  "photos": ["string"],
  "metadata": {}
}
```

#### Get Community Observations
```http
GET /citizen-science/observations
Authorization: Bearer <token>
Query Parameters:
  - observation_type: string (optional)
  - severity: string (optional)
  - status: string (optional)
  - skip: int (default: 0)
  - limit: int (default: 100)
```

#### Get Observation Details
```http
GET /citizen-science/observations/{observation_id}
Authorization: Bearer <token>
```

#### Verify Observation
```http
POST /citizen-science/observations/{observation_id}/verify
Authorization: Bearer <token>
```

#### Respond to Observation
```http
POST /citizen-science/observations/{observation_id}/respond
Authorization: Bearer <token>
Content-Type: application/json

{
  "response_type": "string",
  "response_text": "string"
}
```

#### Upload Submission Photo
```http
POST /citizen-science/submissions/{submission_id}/upload-photo
Authorization: Bearer <token>
Content-Type: multipart/form-data

photo: file
```

#### Get Citizen Science Statistics
```http
GET /citizen-science/stats
Authorization: Bearer <token>
Query Parameters:
  - days: int (default: 30, max: 365)
```

### Geospatial (`/geospatial`)

#### Get Station Locations
```http
GET /geospatial/stations
Authorization: Bearer <token>
Query Parameters:
  - active_only: bool (default: true)
  - bounds: string (optional, format: "min_lat,min_lon,max_lat,max_lon")
```

#### Get Nearby Stations
```http
GET /geospatial/stations/{station_id}/nearby
Authorization: Bearer <token>
Query Parameters:
  - radius_km: float (default: 10.0, max: 100.0)
  - limit: int (default: 20, max: 100)
```

#### Get Map Layers
```http
GET /geospatial/layers
Authorization: Bearer <token>
Query Parameters:
  - layer_types: string (optional, comma-separated)
```

#### Geospatial Query
```http
GET /geospatial/query
Authorization: Bearer <token>
Query Parameters:
  - lat: float
  - lon: float
  - radius_km: float (default: 5.0, max: 50.0)
  - include_stations: bool (default: true)
  - include_aquifer_info: bool (default: true)
```

#### Calculate Distance
```http
GET /geospatial/distance
Authorization: Bearer <token>
Query Parameters:
  - lat1: float
  - lon1: float
  - lat2: float
  - lon2: float
```

#### Get Map Bounds
```http
GET /geospatial/bounds
Authorization: Bearer <token>
```

#### Get Elevation Profile
```http
GET /geospatial/elevation-profile
Authorization: Bearer <token>
Query Parameters:
  - lat1: float
  - lon1: float
  - lat2: float
  - lon2: float
  - points: int (default: 10, max: 100)
```

### Users (`/users`)

#### Get User Profile
```http
GET /users/me
Authorization: Bearer <token>
```

#### Update User Profile
```http
PUT /users/me
Authorization: Bearer <token>
Content-Type: application/json

{
  "username": "string",
  "email": "string",
  "full_name": "string",
  "phone": "string",
  "language": "string",
  "timezone": "string",
  "notification_preferences": {}
}
```

#### Get All Users (Admin)
```http
GET /users/
Authorization: Bearer <token>
Query Parameters:
  - skip: int (default: 0)
  - limit: int (default: 100)
  - active_only: bool (default: true)
```

#### Get User Details (Admin)
```http
GET /users/{user_id}
Authorization: Bearer <token>
```

#### Update User (Admin)
```http
PUT /users/{user_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "username": "string",
  "email": "string",
  "full_name": "string",
  "phone": "string",
  "language": "string",
  "timezone": "string",
  "is_active": bool,
  "is_verified": bool,
  "is_superuser": bool
}
```

#### Deactivate User (Admin)
```http
DELETE /users/{user_id}
Authorization: Bearer <token>
```

#### Get User Usage Permits
```http
GET /users/{user_id}/usage-permits
Authorization: Bearer <token>
Query Parameters:
  - active_only: bool (default: true)
```

#### Create Usage Permit (Admin)
```http
POST /users/{user_id}/usage-permits
Authorization: Bearer <token>
Content-Type: application/json

{
  "station_id": "string",
  "permit_number": "string",
  "total_allocation_m3": float,
  "valid_from": "datetime",
  "valid_until": "datetime",
  "max_daily_usage_m3": float
}
```

#### Get User Usage Records
```http
GET /users/{user_id}/usage-records
Authorization: Bearer <token>
Query Parameters:
  - station_id: string (optional)
  - skip: int (default: 0)
  - limit: int (default: 100)
```

#### Create Usage Record
```http
POST /users/{user_id}/usage-records
Authorization: Bearer <token>
Content-Type: application/json

{
  "permit_id": int,
  "station_id": "string",
  "usage_date": "datetime",
  "volume_m3": float,
  "purpose": "string",
  "crop_type": "string",
  "area_irrigated_hectares": float,
  "notes": "string"
}
```

#### Get All Roles (Admin)
```http
GET /users/roles/
Authorization: Bearer <token>
```

#### Create Role (Admin)
```http
POST /users/roles/
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "string",
  "description": "string",
  "permissions": ["string"]
}
```

## Response Formats

### Success Response
```json
{
  "data": {},
  "message": "string",
  "status": "success"
}
```

### Error Response
```json
{
  "error": "string",
  "message": "string",
  "status": "error",
  "details": {}
}
```

### Paginated Response
```json
{
  "data": [],
  "total": int,
  "skip": int,
  "limit": int,
  "has_more": bool
}
```

## Status Codes

- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

## Rate Limiting

- API endpoints: 10 requests per second per IP
- Authentication endpoints: 5 requests per second per IP
- Rate limit headers are included in responses

## WebSocket Support (Future)

Real-time updates will be available via WebSocket connections for:
- Live sensor data
- Alert notifications
- System status updates

## SDKs and Libraries

Official SDKs are planned for:
- Python
- JavaScript/TypeScript
- Java
- C#

## Support

For API support and questions:
- Check the interactive documentation at `/api/v1/docs`
- Create an issue in the repository
- Contact the development team

## Changelog

### Version 1.0.0
- Initial API release
- Authentication and user management
- Station and sensor management
- Analytics and forecasting
- Notification system
- Citizen science features
- Geospatial services
