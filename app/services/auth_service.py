"""
services/auth_service.py
=========================
Password hashing, OTP generation, and Gmail SMTP email sending.
Uses Gmail App Password (SMTP) — no OAuth required.
"""

import bcrypt
import random
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta


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


# ── Gmail SMTP ────────────────────────────────────────────────────────────────

def _base_template(content: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#0f1117;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f1117;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0"
             style="background:#1a1d27;border-radius:16px;overflow:hidden;border:1px solid #2a2d3e;">
        <tr>
          <td style="background:linear-gradient(135deg,#3b7fff,#6366f1);padding:28px 32px;text-align:center;">
            <h1 style="margin:0;color:#fff;font-size:22px;font-weight:800;">📊 SAPCPOS</h1>
            <p style="margin:4px 0 0;color:rgba(255,255,255,.75);font-size:13px;">
              Student Academic Performance Classification &amp; Pathway Optimization
            </p>
          </td>
        </tr>
        <tr><td style="padding:32px;">{content}</td></tr>
        <tr>
          <td style="padding:20px 32px;border-top:1px solid #2a2d3e;text-align:center;">
            <p style="margin:0;color:#4a4d5e;font-size:12px;">
              Do not share this email. Do not reply.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    sender       = os.getenv('GMAIL_SENDER_EMAIL', '').strip()
    app_password = os.getenv('GMAIL_APP_PASSWORD', '').strip()

    if not sender or not app_password:
        print('[SAPCPOS] Gmail not configured — skipping email.')
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = f'SAPCPOS <{sender}>'
        msg['To']      = to_email
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, app_password)
            server.sendmail(sender, to_email, msg.as_string())

        print(f'[SAPCPOS] Email sent → {to_email}')
        return True
    except Exception as e:
        print(f'[SAPCPOS] Email failed → {to_email}: {e}')
        return False


def send_otp_email(to_email: str, full_name: str, otp: str) -> bool:
    content = f"""
    <p style="color:#94a3b8;font-size:14px;margin:0 0 8px;">Hi {full_name},</p>
    <h2 style="color:#fff;font-size:20px;margin:0 0 16px;">🔐 Your Verification Code</h2>
    <div style="background:#0f1117;border:1px solid #2a2d3e;border-radius:10px;
                padding:24px;margin-bottom:24px;text-align:center;">
      <p style="color:#94a3b8;font-size:13px;margin:0 0 8px;">Your one-time password is:</p>
      <p style="color:#3b7fff;font-size:40px;font-weight:900;letter-spacing:12px;margin:0;">
        {otp}
      </p>
      <p style="color:#4a4d5e;font-size:12px;margin:12px 0 0;">Expires in 10 minutes.</p>
    </div>
    <p style="color:#4a4d5e;font-size:13px;">
      If you did not request this, please ignore this email.
    </p>
    """
    return send_email(
        to_email=to_email,
        subject='🔐 SAPCPOS — Your OTP Verification Code',
        html_body=_base_template(content),
    )


def send_classification_email(to_email: str, full_name: str,
                               classification: str, gpa: float) -> bool:
    badge_color = {'Advanced': '#22c55e', 'Average': '#f59e0b', 'At-Risk': '#ef4444'}
    color = badge_color.get(classification, '#6366f1')
    content = f"""
    <p style="color:#94a3b8;font-size:14px;margin:0 0 8px;">Hi {full_name},</p>
    <h2 style="color:#fff;font-size:20px;margin:0 0 16px;">📊 Your Academic Classification Update</h2>
    <div style="background:#0f1117;border:1px solid #2a2d3e;border-radius:10px;
                padding:24px;margin-bottom:24px;text-align:center;">
      <p style="color:#94a3b8;font-size:13px;margin:0 0 8px;">You have been classified as:</p>
      <p style="color:{color};font-size:28px;font-weight:900;margin:0;">{classification}</p>
      <p style="color:#94a3b8;font-size:14px;margin:12px 0 0;">Current GPA: <strong style="color:#fff;">{gpa:.2f}</strong></p>
    </div>
    <p style="color:#e2e8f0;font-size:14px;">
      Log in to your SAPCPOS dashboard to view your personalized academic pathway recommendations.
    </p>
    """
    return send_email(
        to_email=to_email,
        subject=f'📊 SAPCPOS — Academic Classification: {classification}',
        html_body=_base_template(content),
    )
