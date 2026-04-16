from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User
from app.models.student import Student
from app.services.auth_service import (
    hash_password, verify_password,
    generate_otp, otp_expiry, is_otp_valid,
    send_otp_email,
)
from app.services.notification_service import log_activity

auth_bp = Blueprint('auth', __name__)


# ── Login ─────────────────────────────────────────────────────────────────────

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return _redirect_home()

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()
        if user and user.password_hash and verify_password(password, user.password_hash):
            if not user.is_verified:
                session['pending_user_id'] = user.id
                _send_new_otp(user)
                flash('Please verify your email first.', 'warning')
                return redirect(url_for('auth.verify_otp'))
            login_user(user, remember=True)
            log_activity(user.id, 'LOGIN', f'Email: {email}')
            return _redirect_home()
        flash('Invalid email or password.', 'danger')

    return render_template('auth/login.html')


# ── Register ──────────────────────────────────────────────────────────────────

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return _redirect_home()

    if request.method == 'POST':
        email     = request.form.get('email', '').strip().lower()
        full_name = request.form.get('full_name', '').strip()
        password  = request.form.get('password', '')
        confirm   = request.form.get('confirm_password', '')
        student_id = request.form.get('student_id', '').strip()

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('auth/register.html')

        if Student.query.filter_by(student_id=student_id).first():
            flash('Student ID already exists.', 'danger')
            return render_template('auth/register.html')

        user = User(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            role='student',
            is_verified=False,
        )
        db.session.add(user)
        db.session.flush()  # get user.id

        student = Student(
            user_id=user.id,
            student_id=student_id,
            full_name=full_name,
            email=email,
        )
        db.session.add(student)
        db.session.commit()

        session['pending_user_id'] = user.id
        _send_new_otp(user)
        flash('Registration successful! Check your email for the OTP.', 'success')
        return redirect(url_for('auth.verify_otp'))

    return render_template('auth/register.html')


# ── OTP Verification ──────────────────────────────────────────────────────────

@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    user_id = session.get('pending_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        entered = request.form.get('otp', '').strip()
        if not is_otp_valid(user):
            flash('OTP has expired. Please request a new one.', 'danger')
            return render_template('auth/verify_otp.html', email=user.email)

        if entered == user.otp_code:
            user.is_verified = True
            user.otp_code    = None
            user.otp_expires = None
            db.session.commit()
            session.pop('pending_user_id', None)
            login_user(user, remember=True)
            log_activity(user.id, 'EMAIL_VERIFIED', '')
            flash('Email verified! Welcome.', 'success')
            return _redirect_home()

        flash('Incorrect OTP. Please try again.', 'danger')

    return render_template('auth/verify_otp.html', email=user.email)


@auth_bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    user_id = session.get('pending_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    user = User.query.get(user_id)
    if user:
        _send_new_otp(user)
        flash('A new OTP has been sent to your email.', 'info')
    return redirect(url_for('auth.verify_otp'))


# ── Logout ────────────────────────────────────────────────────────────────────

@auth_bp.route('/logout')
@login_required
def logout():
    log_activity(current_user.id, 'LOGOUT', '')
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _send_new_otp(user: User):
    otp = generate_otp()
    user.otp_code    = otp
    user.otp_expires = otp_expiry(10)
    db.session.commit()
    send_otp_email(user.email, user.full_name, otp)


def _redirect_home():
    from flask_login import current_user
    if current_user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('student.dashboard'))
