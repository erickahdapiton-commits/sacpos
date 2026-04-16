from app import db
from flask_login import UserMixin
from datetime import datetime


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(120), unique=True, nullable=False, index=True)
    full_name     = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)
    role          = db.Column(db.String(20), default='student')   # 'admin' | 'student'
    is_verified   = db.Column(db.Boolean, default=False)
    is_active     = db.Column(db.Boolean, default=True)
    otp_code      = db.Column(db.String(6), nullable=True)
    otp_expires   = db.Column(db.DateTime, nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # One-to-one with Student record
    student = db.relationship('Student', backref='user', uselist=False)
    # Notifications
    notifications = db.relationship('Notification', backref='user', lazy='dynamic',
                                    foreign_keys='Notification.user_id')
    # Activity logs (admin actions)
    logs = db.relationship('ActivityLog', backref='actor', lazy='dynamic',
                           foreign_keys='ActivityLog.user_id')

    def is_admin(self):
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.email}>'
