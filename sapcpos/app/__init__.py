from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from dotenv import load_dotenv
import os

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app():
    base_dir     = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(base_dir, 'templates')
    static_dir   = os.path.join(base_dir, 'static')

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-change-me')

    # ── Turso (production on Vercel) ──────────────────────────────────────────
    turso_url   = os.getenv('TURSO_DATABASE_URL', '')
    turso_token = os.getenv('TURSO_AUTH_TOKEN', '')

    if turso_url and turso_token:
        db_url = f"{turso_url}?authToken={turso_token}"
    else:
        # Local dev fallback — use /tmp (writable on all platforms)
        db_url = os.getenv('DATABASE_URL', 'sqlite:////tmp/sacpos.db')
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)

    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))

    # ── Blueprints ────────────────────────────────────────────────────────────
    from app.controllers.auth_controller      import auth_bp
    from app.controllers.admin_controller     import admin_bp
    from app.controllers.student_controller   import student_bp

    app.register_blueprint(auth_bp,    url_prefix='/auth')
    app.register_blueprint(admin_bp,   url_prefix='/admin')
    app.register_blueprint(student_bp, url_prefix='/student')

    # ── Jinja2 globals
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
        db.create_all()
        _seed_admin()

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
        print(f'[SAPCPOS] Admin seeded: {admin_email}')
