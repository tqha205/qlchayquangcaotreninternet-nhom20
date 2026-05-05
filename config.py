import os
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

# Cấu hình Kết nối MySQL
MYSQL_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),  # Thường để trống nếu dùng XAMPP
    'database': os.getenv('DB_NAME', 'ads_manager_db'),
    'raise_on_warnings': True
}

# Secret key cho Flask Session
SECRET_KEY = os.getenv('SECRET_KEY', 'super_secret_key_rbac_system')

# Cấu hình Telegram (Điền token và chat_id để kích hoạt cảnh báo)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID   = os.getenv('TELEGRAM_CHAT_ID', '')
