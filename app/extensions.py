from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO

db = SQLAlchemy()
migrate = Migrate()
# Dùng threading mode — ổn định trên Windows/Python 3.14, không cần eventlet
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')
