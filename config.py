# Cấu hình Kết nối MySQL
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # Thường để trống nếu dùng XAMPP
    'database': 'ads_manager_db',
    'raise_on_warnings': True
}

# Secret key cho Flask Session
SECRET_KEY = 'super_secret_key_rbac_system'
