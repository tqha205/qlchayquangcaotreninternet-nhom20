import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import timedelta
from flask import Flask
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from app.extensions import db, migrate, socketio, cors, limiter
from config import MYSQL_CONFIG

# Simple Sentry Integration
sentry_sdk.init(
    dsn=os.getenv('SENTRY_DSN', ""), # Bỏ trống nếu chưa có DSN thực
    integrations=[FlaskIntegration()],
    traces_sample_rate=1.0
)

def create_app():
    app = Flask(__name__)
    
    # 1. Logging Configuration
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/ads_manager.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('ADS Manager Startup')

    # Secret key cho Flask Session
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_key_only_for_local_testing')
    app.secret_key = SECRET_KEY

    # SQLAlchemy Config
    db_pass = f":{MYSQL_CONFIG['password']}" if MYSQL_CONFIG['password'] else ""
    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{MYSQL_CONFIG['user']}{db_pass}@{MYSQL_CONFIG['host']}/{MYSQL_CONFIG['database']}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 2. Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})
    limiter.init_app(app)
    from .extensions import csrf
    csrf.init_app(app)

    # Đăng ký SocketIO events
    from app.sockets import register_socket_events
    register_socket_events(socketio)

    # Cấu hình bảo mật session (Timeout 30 phút)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=False, 
        SESSION_COOKIE_SAMESITE='Lax',
    )

    # 3. Đăng ký Blueprints
    from .controllers.auth_controller import auth_bp
    from .controllers.admin_controller import admin_bp
    from .controllers.public_controller import public_bp
    from .controllers.reports_controller import reports_bp

    app.register_blueprint(auth_bp,    url_prefix='/auth')
    app.register_blueprint(admin_bp,   url_prefix='/admin')
    app.register_blueprint(public_bp,  url_prefix='/')
    app.register_blueprint(reports_bp, url_prefix='/admin/reports')

    # Khởi tạo Scheduler (Jobs)
    from app.jobs import init_scheduler
    init_scheduler(app)

    # 4. Đăng ký Filters
    @app.template_filter('format_currency')
    def format_currency(value):
        try:
            return "{:,.0f}".format(value)
        except (ValueError, TypeError):
            return value

    return app
