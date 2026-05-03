"""
services/auth_service.py
=========================
Password hashing, OTP generation, and Gmail API email sending.
Uses Gmail API with OAuth2 service account or user credentials.
"""

import bcrypt
import random
import os
import base64
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta

# Gmail API
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google.auth.transport.requests import Request


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# ── OTP helpers ───────────────────────────────────────────────────────────────

def generate_otp() -> str:
    return str(random.randint(100000, 999999))


def otp_expiry(minutes: int = 10) -> datetime:
    return datetime.utcnow() + timedelta(minutes=minutes)


def is_otp_valid(user) -> bool:
    if not user.otp_code or not user.otp_expires:
        return False
    return datetime.utcnow() < user.otp_expires


# ── Gmail API client ──────────────────────────────────────────────────────────

def _get_gmail_service():
    """
    Build a Gmail API service using one of two strategies:
    
    Strategy 1 — Service Account (recommended for servers):
        Set GMAIL_SERVICE_ACCOUNT_JSON to the full JSON key content (as a string),
        and GMAIL_SENDER_EMAIL to the address the service account impersonates.
        Requires Google Workspace with domain-wide delegation enabled.
    
    Strategy 2 — OAuth2 Refresh Token (recommended for personal Gmail):
        Set GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN,
        and GMAIL_SENDER_EMAIL.
        Get the refresh token by running: python gmail_token_setup.py
    """
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']
    sender = os.getenv('GMAIL_SENDER_EMAIL', '').strip()

    # Strategy 1: Service Account
    sa_json = os.getenv('GMAIL_SERVICE_ACCOUNT_JSON', '').strip()
    if sa_json:
        try:
            sa_info = json.loads(sa_json)
            creds = service_account.Credentials.from_service_account_info(
                sa_info, scopes=SCOPES
            )
            # Impersonate the sender (requires domain-wide delegation)
            if sender:
                creds = creds.with_subject(sender)
            return build('gmail', 'v1', credentials=creds, cache_discovery=False)
        except Exception as e:
            print(f'[SAPCPOS] Service account auth failed: {e}')

    # Strategy 2: OAuth2 Refresh Token
    client_id     = os.getenv('GMAIL_CLIENT_ID', '').strip()
    client_secret = os.getenv('GMAIL_CLIENT_SECRET', '').strip()
    refresh_token = os.getenv('GMAIL_REFRESH_TOKEN', '').strip()

    if client_id and client_secret and refresh_token:
        try:
            creds = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=client_id,
                client_secret=client_secret,
                scopes=SCOPES,
            )
            # Refresh to get a valid access token
            creds.refresh(Request())
            return build('gmail', 'v1', credentials=creds, cache_discovery=False)
        except Exception as e:
            print(f'[SAPCPOS] OAuth2 token auth failed: {e}')

    return None


# ── Email sending ─────────────────────────────────────────────────────────────

def _base_template(content: str) -> str:
    """Sky blue light theme email template."""
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
</head>
<body style="margin:0;padding:0;background:#dff0fb;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0"
         style="background:linear-gradient(135deg,#dff0fb 0%,#bae6fd 100%);padding:48px 16px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:20px;overflow:hidden;
                    border:1px solid #c5dff8;
                    box-shadow:0 8px 40px rgba(14,165,233,0.15);">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#0284c7,#0ea5e9,#38bdf8);
                     padding:32px;text-align:center;">
            <p style="margin:0 0 6px;font-size:30px;">📊</p>
            <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:800;
                       letter-spacing:-0.5px;">SAPCPOS</h1>
            <p style="margin:6px 0 0;color:rgba(255,255,255,0.8);font-size:12px;
                      text-transform:uppercase;letter-spacing:1px;">
              Academic Performance System
            </p>
          </td>
        </tr>

        <!-- Body -->
        <tr><td style="padding:36px 40px;">{content}</td></tr>

        <!-- Footer -->
        <tr>
          <td style="padding:20px 40px 28px;
                     border-top:1px solid #e0f2fe;
                     text-align:center;background:#f0f9ff;">
            <p style="margin:0;color:#94a3b8;font-size:12px;">
              This is an automated message from SAPCPOS. Do not reply.
            </p>
            <p style="margin:6px 0 0;color:#94a3b8;font-size:11px;">
              © 2025 SAPCPOS · Student Academic Performance Classification &amp; Pathway Optimization
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """Send an email via Gmail API."""
    sender = os.getenv('GMAIL_SENDER_EMAIL', '').strip()
    if not sender:
        print('[SAPCPOS] GMAIL_SENDER_EMAIL not set — skipping email.')
        return False

    service = _get_gmail_service()
    if not service:
        print('[SAPCPOS] Gmail API not configured — skipping email.')
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = f'SAPCPOS <{sender}>'
        msg['To']      = to_email
        msg.attach(MIMEText(html_body, 'html'))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()

        print(f'[SAPCPOS] Email sent via Gmail API → {to_email}')
        return True
    except Exception as e:
        print(f'[SAPCPOS] Gmail API send failed → {to_email}: {e}')
        return False


# ── OTP Email ─────────────────────────────────────────────────────────────────

def send_otp_email(to_email: str, full_name: str, otp: str) -> bool:
    digits_html = ''.join(
        f'<span style="display:inline-block;width:46px;height:56px;line-height:56px;'
        f'text-align:center;background:#e0f2fe;border:2px solid #7dd3fc;'
        f'border-radius:12px;font-size:26px;font-weight:900;color:#0284c7;'
        f'margin:0 4px;font-family:monospace;">{d}</span>'
        for d in otp
    )

    content = f"""
    <p style="color:#475569;font-size:15px;margin:0 0 6px;">Hi <strong style="color:#0c4a6e;">{full_name}</strong>,</p>
    <h2 style="color:#0c4a6e;font-size:22px;margin:0 0 20px;font-weight:800;">
      🔐 Your Verification Code
    </h2>

    <div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:14px;
                padding:28px 24px;margin-bottom:24px;text-align:center;">
      <p style="color:#475569;font-size:13px;margin:0 0 16px;font-weight:600;
                text-transform:uppercase;letter-spacing:0.5px;">
        One-Time Password
      </p>
      <div style="margin:0 0 16px;">{digits_html}</div>
      <div style="display:inline-flex;align-items:center;gap:6px;
                  background:#fef3c7;border:1px solid #fcd34d;
                  border-radius:20px;padding:5px 14px;">
        <span style="font-size:13px;">⏱️</span>
        <span style="color:#92400e;font-size:12px;font-weight:700;">Expires in 10 minutes</span>
      </div>
    </div>

    <p style="color:#64748b;font-size:13.5px;line-height:1.7;margin:0 0 12px;">
      Enter this code on the verification page to complete your sign-in.
      If you did not request this, you can safely ignore this email.
    </p>

    <div style="background:#fff7ed;border-left:4px solid #f97316;border-radius:0 8px 8px 0;
                padding:12px 16px;margin-top:20px;">
      <p style="margin:0;color:#9a3412;font-size:13px;font-weight:600;">
        🚨 Never share this code with anyone, including SAPCPOS staff.
      </p>
    </div>
    """
    return send_email(
        to_email=to_email,
        subject='🔐 SAPCPOS — Your OTP Verification Code',
        html_body=_base_template(content),
    )


# ── Classification Email ──────────────────────────────────────────────────────

def send_classification_email(to_email: str, full_name: str,
                               classification: str, gpa: float) -> bool:
    badge = {
        'Advanced': ('🏆', '#059669', '#d1fae5', '#a7f3d0'),
        'Average':  ('📘', '#d97706', '#fef3c7', '#fde68a'),
        'At-Risk':  ('⚠️', '#dc2626', '#fee2e2', '#fca5a5'),
    }
    icon, color, bg, border = badge.get(classification, ('📊', '#0284c7', '#e0f2fe', '#7dd3fc'))

    content = f"""
    <p style="color:#475569;font-size:15px;margin:0 0 6px;">Hi <strong style="color:#0c4a6e;">{full_name}</strong>,</p>
    <h2 style="color:#0c4a6e;font-size:22px;margin:0 0 20px;font-weight:800;">
      📊 Your Academic Classification Update
    </h2>

    <div style="background:{bg};border:2px solid {border};border-radius:16px;
                padding:28px 24px;margin-bottom:24px;text-align:center;">
      <p style="font-size:40px;margin:0 0 8px;">{icon}</p>
      <p style="color:#64748b;font-size:13px;margin:0 0 8px;font-weight:600;
                text-transform:uppercase;letter-spacing:0.5px;">Classification</p>
      <p style="color:{color};font-size:32px;font-weight:900;margin:0 0 16px;
                letter-spacing:-0.5px;">{classification}</p>
      <div style="display:inline-block;background:rgba(255,255,255,0.8);
                  border-radius:10px;padding:10px 24px;border:1px solid {border};">
        <p style="color:#475569;font-size:12px;margin:0 0 2px;font-weight:600;
                  text-transform:uppercase;">Current GPA</p>
        <p style="color:#0c4a6e;font-size:26px;font-weight:900;margin:0;">{gpa:.2f}</p>
      </div>
    </div>

    <p style="color:#475569;font-size:14px;line-height:1.7;margin:0;">
      Log in to your SAPCPOS dashboard to view your personalized academic
      pathway recommendations and improvement plan.
    </p>
    """
    return send_email(
        to_email=to_email,
        subject=f'📊 SAPCPOS — Academic Classification: {classification}',
        html_body=_base_template(content),
    )