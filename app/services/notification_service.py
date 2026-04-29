"""
services/notification_service.py
==================================
Helper to create in-app notifications and activity logs.
"""

from app import db
from app.models.notification import Notification, ActivityLog
from flask import request


def notify(user_id: int, message: str, type: str = 'info'):
    """Create an in-app notification for a user."""
    n = Notification(user_id=user_id, message=message, type=type)
    db.session.add(n)
    db.session.commit()


def log_activity(user_id: int, action: str, detail: str = ''):
    """Write an entry to the activity audit log."""
    ip = request.remote_addr if request else ''
    entry = ActivityLog(user_id=user_id, action=action,
                        detail=detail, ip_address=ip)
    db.session.add(entry)
    db.session.commit()
