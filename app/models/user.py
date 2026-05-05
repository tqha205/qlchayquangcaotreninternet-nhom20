from .base import DBModel
from werkzeug.security import generate_password_hash, check_password_hash

class UserModel(DBModel):

    @staticmethod
    def get_by_auth(username, password):
        """Xác thực người dùng: tìm theo username rồi verify hash."""
        user = DBModel.fetch_one(
            "SELECT * FROM users WHERE username = %s AND is_active = 1",
            (username,)
        )
        if user and check_password_hash(user['password'], password):
            return user
        return None

    @staticmethod
    def get_by_id(user_id):
        """Lấy thông tin user theo ID."""
        return DBModel.fetch_one(
            "SELECT id, username, role, customer_id, is_active FROM users WHERE id = %s",
            (user_id,)
        )

    @staticmethod
    def get_all():
        """Lấy danh sách tất cả người dùng kèm thông tin khách hàng liên kết."""
        query = """
            SELECT u.id, u.username, u.role, u.customer_id, u.is_active, u.created_at,
                   c.name AS customer_name
            FROM users u
            LEFT JOIN customers c ON u.customer_id = c.id
            ORDER BY u.created_at DESC
        """
        return DBModel.fetch_all(query)

    @staticmethod
    def get_by_username(username):
        """Lấy user theo username."""
        return DBModel.fetch_one("SELECT * FROM users WHERE username = %s", (username,))

    @staticmethod
    def create(username, password, role, customer_id=None):
        """Tạo user mới tổng quát."""
        hashed_pw = generate_password_hash(password)
        query = "INSERT INTO users (username, password, role, customer_id) VALUES (%s, %s, %s, %s)"
        return DBModel.execute(query, (username, hashed_pw, role, customer_id))

    @staticmethod
    def update(user_id, username=None, role=None, password=None, customer_id=None):
        """Cập nhật thông tin user."""
        updates = []
        params = []
        if username:
            updates.append("username = %s")
            params.append(username)
        if role:
            updates.append("role = %s")
            params.append(role)
        if password:
            updates.append("password = %s")
            params.append(generate_password_hash(password))
        if customer_id is not None:
            updates.append("customer_id = %s")
            params.append(customer_id if customer_id else None)
        
        if not updates: return False
        
        params.append(user_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = %s"
        return DBModel.execute(query, tuple(params))

    @staticmethod
    def toggle_active(user_id):
        """Đảo ngược trạng thái hoạt động của user."""
        query = "UPDATE users SET is_active = NOT is_active WHERE id = %s"
        return DBModel.execute(query, (user_id,))

    @staticmethod
    def delete(user_id):
        """Xóa user (Cần cẩn thận nếu có ràng buộc FK)."""
        return DBModel.execute("DELETE FROM users WHERE id = %s", (user_id,))

    @staticmethod
    def create_client(username, password, full_name, email=None, phone=None):
        """
        Quy trình đăng ký khách hàng mới:
        1. Tạo record trong bảng customers.
        2. Tạo record trong bảng users với customer_id vừa có.
        """
        # 1. Tạo customer
        sql_cust = "INSERT INTO customers (name, email, phone) VALUES (%s, %s, %s)"
        customer_id = DBModel.execute(sql_cust, (full_name, email, phone))
        
        # 2. Tạo user
        hashed_pw = generate_password_hash(password)
        sql_user = "INSERT INTO users (username, password, role, customer_id) VALUES (%s, %s, %s, %s)"
        user_id = DBModel.execute(sql_user, (username, hashed_pw, 'client', customer_id))
        
        return user_id
