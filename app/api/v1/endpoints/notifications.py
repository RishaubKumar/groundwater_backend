"""
Notification and alert endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.analytics import Alert
from app.services.notifications import NotificationService
from app.schemas.notifications import AlertResponse, NotificationPreferences

router = APIRouter()


@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    station_id: Optional[str] = Query(None, description="Filter by station ID"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    active_only: bool = Query(True, description="Show only active alerts"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get alerts."""
    query = db.query(Alert)
    
    if station_id:
        query = query.filter(Alert.station_id == station_id)
    
    if severity:
        query = query.filter(Alert.severity == severity)
    
    if active_only:
        query = query.filter(Alert.is_active == True)
    
    alerts = query.order_by(Alert.created_at.desc()).offset(skip).limit(limit).all()
    
    return [
        {
            'id': alert.id,
            'station_id': alert.station_id,
            'alert_type': alert.alert_type,
            'severity': alert.severity,
            'title': alert.title,
            'message': alert.message,
            'created_at': alert.created_at.isoformat(),
            'acknowledged': alert.acknowledged,
            'acknowledged_by': alert.acknowledged_by,
            'acknowledged_at': alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
            'metadata': alert.metadata
        }
        for alert in alerts
    ]


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int = Path(..., description="Alert ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get specific alert."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {
        'id': alert.id,
        'station_id': alert.station_id,
        'alert_type': alert.alert_type,
        'severity': alert.severity,
        'title': alert.title,
        'message': alert.message,
        'created_at': alert.created_at.isoformat(),
        'acknowledged': alert.acknowledged,
        'acknowledged_by': alert.acknowledged_by,
        'acknowledged_at': alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        'metadata': alert.metadata
    }


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int = Path(..., description="Alert ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Acknowledge an alert."""
    notification_service = NotificationService()
    
    success = await notification_service.acknowledge_alert(alert_id, current_user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"message": "Alert acknowledged successfully"}


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int = Path(..., description="Alert ID"),
    resolution_notes: Optional[str] = Query(None, description="Resolution notes"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Resolve an alert."""
    notification_service = NotificationService()
    
    success = await notification_service.resolve_alert(alert_id, resolution_notes)
    
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"message": "Alert resolved successfully"}


@router.get("/preferences")
async def get_notification_preferences(
    current_user: User = Depends(get_current_active_user)
):
    """Get user's notification preferences."""
    return {
        "user_id": current_user.id,
        "preferences": current_user.notification_preferences or {},
        "language": current_user.language,
        "timezone": current_user.timezone
    }


@router.put("/preferences")
async def update_notification_preferences(
    preferences: NotificationPreferences,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user's notification preferences."""
    current_user.notification_preferences = preferences.dict()
    current_user.language = preferences.language
    current_user.timezone = preferences.timezone
    
    db.commit()
    
    return {"message": "Notification preferences updated successfully"}


@router.post("/fcm-token")
async def update_fcm_token(
    token: str = Query(..., description="FCM token"),
    current_user: User = Depends(get_current_active_user)
):
    """Update user's FCM token for push notifications."""
    notification_service = NotificationService()
    
    success = await notification_service.update_user_fcm_token(current_user.id, token)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update FCM token")
    
    return {"message": "FCM token updated successfully"}


@router.post("/test-notification")
async def send_test_notification(
    title: str = Query(..., description="Notification title"),
    body: str = Query(..., description="Notification body"),
    current_user: User = Depends(get_current_active_user)
):
    """Send test notification to current user."""
    notification_service = NotificationService()
    
    success = await notification_service.send_push_notification(
        current_user.id, title, body
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to send test notification")
    
    return {"message": "Test notification sent successfully"}


@router.get("/stats")
async def get_notification_stats(
    days: int = Query(30, ge=1, le=365, description="Period in days"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get notification statistics."""
    start_date = datetime.now() - timedelta(days=days)
    
    # Get alert statistics
    total_alerts = db.query(Alert).filter(Alert.created_at >= start_date).count()
    active_alerts = db.query(Alert).filter(
        Alert.created_at >= start_date,
        Alert.is_active == True
    ).count()
    acknowledged_alerts = db.query(Alert).filter(
        Alert.created_at >= start_date,
        Alert.acknowledged == True
    ).count()
    
    # Get alerts by severity
    severity_stats = {}
    for severity in ['low', 'medium', 'high', 'critical']:
        count = db.query(Alert).filter(
            Alert.created_at >= start_date,
            Alert.severity == severity
        ).count()
        severity_stats[severity] = count
    
    # Get alerts by type
    alert_type_stats = {}
    alert_types = db.query(Alert.alert_type).filter(
        Alert.created_at >= start_date
    ).distinct().all()
    
    for alert_type, in alert_types:
        count = db.query(Alert).filter(
            Alert.created_at >= start_date,
            Alert.alert_type == alert_type
        ).count()
        alert_type_stats[alert_type] = count
    
    return {
        "period_days": days,
        "total_alerts": total_alerts,
        "active_alerts": active_alerts,
        "acknowledged_alerts": acknowledged_alerts,
        "severity_breakdown": severity_stats,
        "type_breakdown": alert_type_stats,
        "acknowledgment_rate": acknowledged_alerts / total_alerts if total_alerts > 0 else 0
    }
