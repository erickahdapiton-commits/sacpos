from app import db
from datetime import datetime


class Notification(db.Model):
    __tablename__ = 'notifications'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    message    = db.Column(db.Text, nullable=False)
    type       = db.Column(db.String(30), default='info')   # 'info'|'warning'|'success'|'danger'
    is_read    = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Notification {self.id} → user {self.user_id}>'


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    action     = db.Column(db.String(100), nullable=False)
    detail     = db.Column(db.Text, default='')
    ip_address = db.Column(db.String(45), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ActivityLog {self.action} by user {self.user_id}>'
