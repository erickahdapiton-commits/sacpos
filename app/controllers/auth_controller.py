import os
import secrets
import requests as http_requests
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

# ── Google OAuth config ───────────────────────────────────────────────────────
GOOGLE_CLIENT_ID     = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI  = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/google/callback')

GOOGLE_AUTH_URL  = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO  = 'https://www.googleapis.com/oauth2/v3/userinfo'


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
        email      = request.form.get('email', '').strip().lower()
        full_name  = request.form.get('full_name', '').strip()
        password   = request.form.get('password', '')
        confirm    = request.form.get('confirm_password', '')
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
        db.session.flush()

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


# ── Google OAuth ──────────────────────────────────────────────────────────────

@auth_bp.route('/google/login')
def google_login():
    if not GOOGLE_CLIENT_ID:
        flash('Google Sign-In is not configured yet. Contact the administrator.', 'warning')
        return redirect(url_for('auth.login'))

    state = secrets.token_urlsafe(16)
    session['oauth_state'] = state

    params = {
        'client_id':     GOOGLE_CLIENT_ID,
        'redirect_uri':  GOOGLE_REDIRECT_URI,
        'response_type': 'code',
        'scope':         'openid email profile',
        'state':         state,
        'access_type':   'online',
        'prompt':        'select_account',
    }
    query = '&'.join(f'{k}={v}' for k, v in params.items())
    return redirect(f'{GOOGLE_AUTH_URL}?{query}')


@auth_bp.route('/google/callback')
def google_callback():
    # Validate state
    if request.args.get('state') != session.pop('oauth_state', None):
        flash('OAuth state mismatch. Please try again.', 'danger')
        return redirect(url_for('auth.login'))

    error = request.args.get('error')
    if error:
        flash(f'Google sign-in was cancelled or failed: {error}', 'danger')
        return redirect(url_for('auth.login'))

    code = request.args.get('code')
    if not code:
        flash('No authorisation code received from Google.', 'danger')
        return redirect(url_for('auth.login'))

    # Exchange code for tokens
    token_resp = http_requests.post(GOOGLE_TOKEN_URL, data={
        'code':          code,
        'client_id':     GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'redirect_uri':  GOOGLE_REDIRECT_URI,
        'grant_type':    'authorization_code',
    })

    if not token_resp.ok:
        flash('Failed to retrieve Google access token.', 'danger')
        return redirect(url_for('auth.login'))

    access_token = token_resp.json().get('access_token')

    # Fetch user info
    userinfo_resp = http_requests.get(
        GOOGLE_USERINFO,
        headers={'Authorization': f'Bearer {access_token}'}
    )

    if not userinfo_resp.ok:
        flash('Failed to retrieve Google user info.', 'danger')
        return redirect(url_for('auth.login'))

    info      = userinfo_resp.json()
    google_id = info.get('sub')
    email     = info.get('email', '').lower().strip()
    full_name = info.get('name', email.split('@')[0])

    if not email:
        flash('Could not get email from Google. Please use email/password sign-in.', 'danger')
        return redirect(url_for('auth.login'))

    # Find or create user
    user = User.query.filter_by(email=email).first()

    if user:
        # Existing user — log in directly (Google-verified email)
        if not user.is_active:
            flash('Your account has been deactivated.', 'danger')
            return redirect(url_for('auth.login'))
        user.is_verified = True           # Google email is trusted
        db.session.commit()
        login_user(user, remember=True)
        log_activity(user.id, 'GOOGLE_LOGIN', f'Google ID: {google_id}')
        flash(f'Welcome back, {user.full_name}!', 'success')
        return _redirect_home()
    else:
        # New user via Google — create account, skip OTP
        user = User(
            email=email,
            full_name=full_name,
            password_hash=None,   # No password for Google accounts
            role='student',
            is_verified=True,     # Google already verified
        )
        db.session.add(user)
        db.session.flush()

        # We need a unique student_id; generate a placeholder the admin can update
        import re
        safe_name = re.sub(r'[^a-z0-9]', '', full_name.lower())[:8]
        placeholder_id = f'G-{safe_name[:6]}-{user.id}'

        student = Student(
            user_id=user.id,
            student_id=placeholder_id,
            full_name=full_name,
            email=email,
        )
        db.session.add(student)
        db.session.commit()

        login_user(user, remember=True)
        log_activity(user.id, 'GOOGLE_REGISTER', f'Google ID: {google_id}')
        flash(
            'Account created via Google! Your temporary Student ID is '
            f'<strong>{placeholder_id}</strong>. Please ask your admin to update it.',
            'info'
        )
        return _redirect_home()


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
