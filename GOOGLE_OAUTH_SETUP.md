# Google OAuth Setup for SAPCPOS

## 1. Google Cloud Console

1. Go to https://console.cloud.google.com/
2. Create a new project (or select your existing one)
3. Navigate to **APIs & Services → Credentials**
4. Click **Create Credentials → OAuth 2.0 Client IDs**
5. Set Application type to **Web application**
6. Add Authorized Redirect URIs:
   - Local dev: `http://localhost:5000/auth/google/callback`
   - Production: `https://your-vercel-domain.vercel.app/auth/google/callback`
7. Copy your **Client ID** and **Client Secret**

## 2. Environment Variables

Add these to your `.env` file (local) or Vercel environment settings (production):

```env
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret-here

# Existing vars (keep these)
SECRET_KEY=your-flask-secret-key
GMAIL_SENDER_EMAIL=your@gmail.com
GMAIL_APP_PASSWORD=your-gmail-app-password
```

## 3. Install the new dependency

```bash
pip install Authlib==1.3.0
# or
pip install -r requirements.txt
```

## 4. Database Migration

The User model has two new columns (`google_id`, `avatar_url`).
Run migrations:

```bash
flask db migrate -m "add google oauth fields"
flask db upgrade
```

Or if you're using SQLite locally and just want to reset:

```bash
flask db upgrade
```

## How it works

- **Login page** → "Continue with Google" → Google OAuth consent → callback
- If the email already exists, the account is linked to Google (no password needed next time)
- If the email is new, a student account is created automatically with a placeholder Student ID (`G-XXXXX`) that an admin can update later
- Google users bypass OTP verification (their email is already verified by Google)
