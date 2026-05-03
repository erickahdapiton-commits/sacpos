from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import os
import re

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
oauth = OAuth()


def create_app():
    base_dir     = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(base_dir, 'templates')
    static_dir   = os.path.join(base_dir, 'static')

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-change-me')

    # ── Database ──────────────────────────────────────────────────────────────
    turso_url   = os.getenv('TURSO_DATABASE_URL', '')
    turso_token = os.getenv('TURSO_AUTH_TOKEN', '')
    is_vercel   = os.getenv('VERCEL') or os.getenv('VERCEL_ENV')

    if turso_url and turso_token:
        # sqlalchemy-libsql connects via WebSocket (wss://) which Vercel
        # serverless blocks → "505 Invalid response status".
        # Fix: use our turso_http shim which calls libsql-client with an
        # https:// URL, routing all traffic through Turso's HTTP API instead.
        from app.turso_http import connect as turso_connect
        from sqlalchemy.pool import NullPool

        https_url = re.sub(r'^libsql://', 'https://', turso_url)

        # Dummy URI — the actual connection comes from the creator callable.
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite+pysqlite://'
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'creator': lambda: turso_connect(url=https_url, auth_token=turso_token),
            'poolclass': NullPool,   # no persistent pool on serverless
        }

    elif is_vercel:
        # Vercel but no Turso creds — fail loudly
        raise RuntimeError(
            "TURSO_DATABASE_URL and TURSO_AUTH_TOKEN must be set in Vercel "
            "environment variables. Got: "
            f"TURSO_DATABASE_URL={'set' if turso_url else 'MISSING'}, "
            f"TURSO_AUTH_TOKEN={'set' if turso_token else 'MISSING'}"
        )
    else:
        # Local dev — plain SQLite
        db_url = os.getenv('DATABASE_URL', 'sqlite:////tmp/sacpos.db')
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    oauth.init_app(app)

    oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID', ''),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET', ''),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))

    # ── Blueprints ────────────────────────────────────────────────────────────
    from app.controllers.auth_controller    import auth_bp
    from app.controllers.admin_controller   import admin_bp
    from app.controllers.student_controller import student_bp

    app.register_blueprint(auth_bp,    url_prefix='/auth')
    app.register_blueprint(admin_bp,   url_prefix='/admin')
    app.register_blueprint(student_bp, url_prefix='/student')

    # ── Jinja2 globals ────────────────────────────────────────────────────────
    app.jinja_env.globals['enumerate'] = enumerate
    app.jinja_env.globals['zip']       = zip

    @app.route('/')
    def index():
        from flask import redirect, url_for
        from flask_login import current_user
        if current_user.is_authenticated:
            if current_user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('student.dashboard'))
        return redirect(url_for('auth.login'))

    # ── Seed DB ───────────────────────────────────────────────────────────────
    with app.app_context():
        try:
            db.create_all()
            _seed_admin()
        except Exception as e:
            import sys
            print(f"[SACPOS] DB init skipped: {e}", file=sys.stderr)

    return app


def _seed_admin():
    from app.models.user import User
    from app.services.auth_service import hash_password

    admin_email = os.getenv('ADMIN_EMAIL', 'admin@school.edu')
    admin_pass  = os.getenv('ADMIN_PASSWORD', 'AdminPass123')
    admin_name  = os.getenv('ADMIN_NAME', 'System Administrator')

    if not User.query.filter_by(email=admin_email).first():
        admin = User(
            email=admin_email,
            full_name=admin_name,
            password_hash=hash_password(admin_pass),
            role='admin',
            is_verified=True,
        )
        db.session.add(admin)
        db.session.commit()
        print(f'[SACPOS] Admin seeded: {admin_email}')
