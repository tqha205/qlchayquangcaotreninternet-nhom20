from flask import Flask
from flask_wtf.csrf import CSRFProtect
from datetime import timedelta
import os
from config import SECRET_KEY, MYSQL_CONFIG
from app.extensions import db, migrate, socketio

def create_app():
    app = Flask(__name__)
    app.secret_key = SECRET_KEY

    # SQLAlchemy Config
    # Xử lý mật khẩu rỗng nếu dùng XAMPP
    db_pass = f":{MYSQL_CONFIG['password']}" if MYSQL_CONFIG['password'] else ""
    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{MYSQL_CONFIG['user']}{db_pass}@{MYSQL_CONFIG['host']}/{MYSQL_CONFIG['database']}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)

    # Đăng ký SocketIO events
    from app.sockets import register_socket_events
    register_socket_events(socketio)

    # Cấu hình bảo mật session (Timeout 30 phút)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

    # Kích hoạt CSRF Protection toàn cục
    # csrf = CSRFProtect()
    # csrf.init_app(app)

    # Đăng ký Blueprints
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

    # Đăng ký Filters
    @app.template_filter('format_currency')
    def format_currency(value):
        try:
            return "{:,.0f}".format(value)
        except (ValueError, TypeError):
            return value

    return app
