from flask import Flask
import os
from config import SECRET_KEY

def create_app():
    app = Flask(__name__)
    app.secret_key = SECRET_KEY

    # Đăng ký Blueprints
    from .auth.routes import auth_bp
    from .admin.routes import admin_bp
    from .public.routes import public_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(public_bp, url_prefix='/')

    return app
