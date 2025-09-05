"""
Notification and alerting services.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import firebase_admin
from firebase_admin import credentials, messaging
import boto3
from app.core.config import settings
from app.core.database import get_db, get_redis_client
from app.models.analytics import Alert
from app.models.user import User

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications and managing alerts."""
    
    def __init__(self):
        self.redis_client = get_redis_client()
        self.firebase_app = None
        self.sns_client = None
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize notification services."""
        try:
            # Initialize Firebase
            if settings.FIREBASE_CREDENTIALS_PATH:
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                self.firebase_app = firebase_admin.initialize_app(cred)
                logger.info("Firebase initialized successfully")
            
            # Initialize AWS SNS
            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                self.sns_client = boto3.client(
                    'sns',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION
                )
                logger.info("AWS SNS initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing notification services: {e}")
    
    async def send_push_notification(self, user_id: int, title: str, body: str, 
                                   data: Dict[str, str] = None) -> bool:
        """Send push notification to a user."""
        try:
            if not self.firebase_app:
                logger.warning("Firebase not initialized")
                return False
            
            # Get user's FCM token
            fcm_token = await self._get_user_fcm_token(user_id)
            if not fcm_token:
                logger.warning(f"No FCM token for user {user_id}")
                return False
            
            # Create message
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data or {},
                token=fcm_token
            )
            
            # Send message
            response = messaging.send(message)
            logger.info(f"Push notification sent to user {user_id}: {response}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending push notification: {e}")
            return False
    
    async def send_sms_notification(self, phone_number: str, message: str) -> bool:
        """Send SMS notification."""
        try:
            if not self.sns_client:
                logger.warning("SNS not initialized")
                return False
            
            response = self.sns_client.publish(
                PhoneNumber=phone_number,
                Message=message
            )
            
            logger.info(f"SMS sent to {phone_number}: {response['MessageId']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return False
    
    async def send_email_notification(self, email: str, subject: str, body: str) -> bool:
        """Send email notification."""
        try:
            if not self.sns_client:
                logger.warning("SNS not initialized")
                return False
            
            # For email, we would typically use SES, but using SNS for simplicity
            response = self.sns_client.publish(
                TopicArn=settings.SNS_TOPIC_ARN,
                Subject=subject,
                Message=body,
                MessageAttributes={
                    'email': {
                        'DataType': 'String',
                        'StringValue': email
                    }
                }
            )
            
            logger.info(f"Email sent to {email}: {response['MessageId']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    async def create_alert(self, station_id: str, alert_type: str, severity: str, 
                          title: str, message: str, metadata: Dict[str, Any] = None) -> int:
        """Create a new alert."""
        try:
            db = next(get_db())
            
            alert = Alert(
                station_id=station_id,
                alert_type=alert_type,
                severity=severity,
                title=title,
                message=message,
                metadata=metadata or {}
            )
            
            db.add(alert)
            db.commit()
            db.refresh(alert)
            
            # Send notifications to subscribed users
            await self._notify_subscribed_users(alert)
            
            logger.info(f"Created alert {alert.id} for station {station_id}")
            return alert.id
            
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            return 0
        finally:
            db.close()
    
    async def _notify_subscribed_users(self, alert: Alert):
        """Notify users subscribed to alerts for this station."""
        try:
            # Get users subscribed to this station
            subscribed_users = await self._get_subscribed_users(alert.station_id)
            
            for user in subscribed_users:
                # Check if user wants this type of alert
                if await self._should_notify_user(user, alert):
                    # Send push notification
                    await self.send_push_notification(
                        user.id,
                        alert.title,
                        alert.message,
                        {
                            'alert_id': str(alert.id),
                            'station_id': alert.station_id,
                            'alert_type': alert.alert_type,
                            'severity': alert.severity
                        }
                    )
                    
                    # Send email for critical alerts
                    if alert.severity == 'critical':
                        await self.send_email_notification(
                            user.email,
                            f"CRITICAL: {alert.title}",
                            alert.message
                        )
            
        except Exception as e:
            logger.error(f"Error notifying subscribed users: {e}")
    
    async def _get_subscribed_users(self, station_id: str) -> List[User]:
        """Get users subscribed to alerts for a station."""
        try:
            db = next(get_db())
            
            # This would typically query a subscription table
            # For now, return all active users
            users = db.query(User).filter(User.is_active == True).all()
            return users
            
        except Exception as e:
            logger.error(f"Error getting subscribed users: {e}")
            return []
        finally:
            db.close()
    
    async def _should_notify_user(self, user: User, alert: Alert) -> bool:
        """Check if user should be notified about this alert."""
        try:
            # Check user's notification preferences
            prefs = user.notification_preferences or {}
            
            # Check if user wants this alert type
            alert_types = prefs.get('alert_types', ['all'])
            if 'all' not in alert_types and alert.alert_type not in alert_types:
                return False
            
            # Check if user wants this severity level
            severities = prefs.get('severities', ['medium', 'high', 'critical'])
            if alert.severity not in severities:
                return False
            
            # Check if user is subscribed to this station
            subscribed_stations = prefs.get('stations', [])
            if subscribed_stations and alert.station_id not in subscribed_stations:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking user notification preferences: {e}")
            return True  # Default to sending notification
    
    async def _get_user_fcm_token(self, user_id: int) -> Optional[str]:
        """Get user's FCM token."""
        try:
            # This would typically be stored in the database
            # For now, get from Redis cache
            token_key = f"fcm_token:{user_id}"
            token = self.redis_client.get(token_key)
            return token.decode() if token else None
            
        except Exception as e:
            logger.error(f"Error getting FCM token: {e}")
            return None
    
    async def update_user_fcm_token(self, user_id: int, token: str) -> bool:
        """Update user's FCM token."""
        try:
            token_key = f"fcm_token:{user_id}"
            self.redis_client.set(token_key, token, ex=86400 * 30)  # 30 days
            logger.info(f"Updated FCM token for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating FCM token: {e}")
            return False
    
    async def send_bulk_notification(self, user_ids: List[int], title: str, body: str,
                                   data: Dict[str, str] = None) -> Dict[str, int]:
        """Send notification to multiple users."""
        try:
            results = {'success': 0, 'failed': 0}
            
            for user_id in user_ids:
                success = await self.send_push_notification(user_id, title, body, data)
                if success:
                    results['success'] += 1
                else:
                    results['failed'] += 1
            
            logger.info(f"Bulk notification sent: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error sending bulk notification: {e}")
            return {'success': 0, 'failed': 0}
    
    async def get_active_alerts(self, station_id: str = None) -> List[Dict[str, Any]]:
        """Get active alerts."""
        try:
            db = next(get_db())
            
            query = db.query(Alert).filter(Alert.is_active == True)
            
            if station_id:
                query = query.filter(Alert.station_id == station_id)
            
            alerts = query.order_by(Alert.created_at.desc()).all()
            
            return [
                {
                    'id': alert.id,
                    'station_id': alert.station_id,
                    'alert_type': alert.alert_type,
                    'severity': alert.severity,
                    'title': alert.title,
                    'message': alert.message,
                    'created_at': alert.created_at.isoformat(),
                    'acknowledged': alert.acknowledged
                }
                for alert in alerts
            ]
            
        except Exception as e:
            logger.error(f"Error getting active alerts: {e}")
            return []
        finally:
            db.close()
    
    async def acknowledge_alert(self, alert_id: int, user_id: int) -> bool:
        """Acknowledge an alert."""
        try:
            db = next(get_db())
            
            alert = db.query(Alert).filter(Alert.id == alert_id).first()
            if not alert:
                return False
            
            alert.acknowledged = True
            alert.acknowledged_by = str(user_id)
            alert.acknowledged_at = datetime.now()
            
            db.commit()
            
            logger.info(f"Alert {alert_id} acknowledged by user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")
            return False
        finally:
            db.close()
    
    async def resolve_alert(self, alert_id: int, resolution_notes: str = None) -> bool:
        """Resolve an alert."""
        try:
            db = next(get_db())
            
            alert = db.query(Alert).filter(Alert.id == alert_id).first()
            if not alert:
                return False
            
            alert.is_active = False
            if resolution_notes:
                alert.metadata = alert.metadata or {}
                alert.metadata['resolution_notes'] = resolution_notes
            
            db.commit()
            
            logger.info(f"Alert {alert_id} resolved")
            return True
            
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
            return False
        finally:
            db.close()
    
    async def cleanup_old_alerts(self, days: int = 30):
        """Clean up old resolved alerts."""
        try:
            db = next(get_db())
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Mark old resolved alerts as inactive
            old_alerts = db.query(Alert).filter(
                Alert.is_active == False,
                Alert.acknowledged == True,
                Alert.created_at < cutoff_date
            ).all()
            
            for alert in old_alerts:
                alert.is_active = False
            
            db.commit()
            
            logger.info(f"Cleaned up {len(old_alerts)} old alerts")
            
        except Exception as e:
            logger.error(f"Error cleaning up old alerts: {e}")
        finally:
            db.close()
    
    async def send_maintenance_reminder(self, station_id: str, maintenance_type: str, 
                                      due_date: datetime) -> bool:
        """Send maintenance reminder."""
        try:
            title = f"Maintenance Reminder - {station_id}"
            message = f"{maintenance_type} maintenance is due on {due_date.strftime('%Y-%m-%d')}"
            
            # Get station administrators
            admin_users = await self._get_station_administrators(station_id)
            
            if admin_users:
                await self.send_bulk_notification(
                    [user.id for user in admin_users],
                    title,
                    message,
                    {
                        'station_id': station_id,
                        'maintenance_type': maintenance_type,
                        'due_date': due_date.isoformat()
                    }
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending maintenance reminder: {e}")
            return False
    
    async def _get_station_administrators(self, station_id: str) -> List[User]:
        """Get administrators for a station."""
        try:
            db = next(get_db())
            
            # This would typically query a station_administrators table
            # For now, return users with admin role
            admin_users = db.query(User).filter(
                User.is_active == True,
                User.is_superuser == True
            ).all()
            
            return admin_users
            
        except Exception as e:
            logger.error(f"Error getting station administrators: {e}")
            return []
        finally:
            db.close()
