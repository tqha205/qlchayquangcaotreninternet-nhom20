from app import create_app
from app.extensions import db
from app.models import UserModel
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    admin_user = UserModel.query.filter_by(username='admin').first()
    if admin_user:
        admin_user.password = generate_password_hash('Admin@123', method='scrypt')
        db.session.commit()
        print("Mật khẩu admin đã được khôi phục thành Admin@123")
    else:
        print("Không tìm thấy tài khoản admin!")
