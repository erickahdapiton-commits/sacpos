# 📊 SAPCPOS
## Student Academic Performance Classification & Pathway Optimization System

A Flask web application for tracking, classifying, and guiding students using
three core algorithms: **Decision Tree** (classification), **QuickSort** (ranking),
and **Dijkstra's algorithm** (pathway optimization).

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔐 Authentication | Email + OTP via Gmail SMTP, role-based access (Admin / Student) |
| 👥 Student Management | Full CRUD — add, edit, delete student records with GPA, attendance, failures, trend, subject scores |
| 🌲 Decision Tree | Classifies students as **Advanced**, **Average**, or **At-Risk** |
| 🏆 QuickSort Ranking | Ranks students by GPA — O(n log n) |
| 🗺️ Dijkstra Pathway | Shortest academic path through 14-course curriculum graph |
| 📈 Analytics | Charts: classification distribution, trend, scatter (attendance vs GPA), GPA histogram |
| 🔔 Notifications | In-app alerts + Gmail email when classification changes |
| 📋 Audit Log | Full admin activity trail with timestamps and IPs |
| 🎯 Student Profile | Students set interests (STEM / Business / Arts), get personalized pathway |
| 🔍 Search & Filter | By name, student ID, or classification |

---

## 🗂 Project Structure

```
sapcpos/
├── api/
│   └── index.py                  # Vercel entry point
├── app/
│   ├── __init__.py               # App factory
│   ├── algorithms/
│   │   ├── decision_tree.py      # O(1) classification tree
│   │   ├── quicksort.py          # O(n log n) ranking
│   │   └── dijkstra.py           # O((V+E) log V) pathway
│   ├── controllers/
│   │   ├── auth_controller.py    # Login, register, OTP
│   │   ├── admin_controller.py   # Dashboard, CRUD, analytics, logs
│   │   └── student_controller.py # Student dashboard, pathway, profile
│   ├── models/
│   │   ├── user.py
│   │   ├── student.py
│   │   └── notification.py       # Notification + ActivityLog
│   ├── services/
│   │   ├── auth_service.py       # Bcrypt, OTP, Gmail SMTP
│   │   └── notification_service.py
│   ├── static/
│   │   ├── css/main.css
│   │   └── js/main.js
│   └── templates/
│       ├── partials/base.html
│       ├── auth/                 # login, register, verify_otp
│       ├── admin/                # dashboard, students, rankings, analytics, logs
│       └── student/              # dashboard, profile, pathway, rankings
├── requirements.txt
├── vercel.json
└── .env.example
```

---

## 🚀 Local Setup

### 1. Clone & create virtual environment
```bash
git clone <your-repo>
cd sapcpos
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables
```bash
cp .env.example .env
# Edit .env with your values
```

### 4. Run locally
```bash
flask --app api.index run --debug
```

Visit `http://localhost:5000`

**Default admin:** `admin@school.edu` / `AdminPass123` (set in `.env`)

---

## ☁️ Deploy to Vercel

### 1. Push to GitHub
```bash
git init
git add .
git commit -m "Initial SAPCPOS commit"
git remote add origin https://github.com/youruser/sapcpos.git
git push -u origin main
```

### 2. Import to Vercel
- Go to [vercel.com](https://vercel.com) → **Add New Project**
- Import your GitHub repo
- Framework: **Other**

### 3. Add Environment Variables in Vercel dashboard
```
SECRET_KEY          = your-long-random-secret
DATABASE_URL        = your-postgresql-url   ← use Neon, Supabase, or Railway
GMAIL_SENDER_EMAIL  = yourapp@gmail.com
GMAIL_APP_PASSWORD  = xxxx-xxxx-xxxx-xxxx
ADMIN_EMAIL         = admin@yourschool.edu
ADMIN_PASSWORD      = StrongAdminPass123
ADMIN_NAME          = System Administrator
```

### 4. Deploy
Vercel will auto-deploy. The `vercel.json` and `api/index.py` handle the routing.

> ⚠️ **Database note:** Vercel serverless functions have no persistent filesystem.
> Use a hosted PostgreSQL database (Neon is free): `DATABASE_URL=postgresql://...`

---

## 📧 Gmail App Password Setup

1. Enable 2-Step Verification on your Google account
2. Go to **Google Account → Security → App Passwords**
3. Generate a password for "Mail"
4. Set `GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx` in your `.env`

---

## 🧠 Algorithms

### Decision Tree — `app/algorithms/decision_tree.py`
Fixed-depth tree with 3 nodes:
- **Node 1:** Is GPA ≥ 3.0 (failing range)? → check failures/attendance/trend → **At-Risk**
- **Node 2:** Is GPA ≤ 1.75 (excellent)? → check attendance/failures → **Advanced**
- **Node 3:** GPA 1.76–2.99 (average range) → check failures/trend → **Average** or **At-Risk**

### QuickSort — `app/algorithms/quicksort.py`
Standard in-place QuickSort. Sorts student list by GPA attribute.
Philippine scale: 1.0 (best) → 5.0 (fail), so rank #1 = lowest GPA.

### Dijkstra — `app/algorithms/dijkstra.py`
Min-heap Dijkstra on a 14-node curriculum graph.
Three track entry points: **Math** (STEM), **Econ** (Business), **FilLit** (Arts).
All tracks converge toward **Research** (capstone).
Edge weights = subject transition difficulty (1–5).

---

## 👤 Default Accounts

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@school.edu` | `AdminPass123` |
| Student | Registered via `/auth/register` | Set by user |

> Admin can also add students directly; their default password becomes their **Student ID**.

---

## 🛠 Tech Stack

- **Backend:** Flask 3.0, Flask-SQLAlchemy, Flask-Login, Flask-Migrate
- **Database:** SQLite (local) / PostgreSQL (production)
- **Auth:** bcrypt + Gmail SMTP OTP
- **Charts:** Chart.js 4 (CDN)
- **Deploy:** Vercel (serverless Python)
