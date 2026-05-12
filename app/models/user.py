from app.extensions import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class UserModel(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='client') # 'admin', 'marketer', 'client'
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = db.relationship('CustomerModel', foreign_keys=[customer_id], backref=db.backref('user', uselist=False))

    @staticmethod
    def get_by_auth(username, password):
        user = UserModel.query.filter_by(username=username, is_active=True).first()
        if user and check_password_hash(user.password, password):
            return user
        return None

    @staticmethod
    def get_by_id(user_id):
        return UserModel.query.get(user_id)

    @staticmethod
    def get_all():
        """Lấy tất cả người dùng kèm tên khách hàng liên kết bằng SQL thuần để tránh lỗi ORM."""
        from .base import DBModel
        sql = """
            SELECT 
                u.id, u.username, u.role, u.customer_id, u.is_active, u.created_at,
                c.name AS linked_customer_name
            FROM users u
            LEFT JOIN customers c ON u.customer_id = c.id
            ORDER BY u.created_at DESC
        """
        rows = DBModel.fetch_all(sql)
        
        result = []
        for r in rows:
            # Lấy số lượng khách hàng quản lý (nếu là marketer)
            managed_count = 0
            if r['role'] == 'marketer':
                m_sql = "SELECT COUNT(*) as cnt FROM customers WHERE marketer_id = %s AND is_deleted = 0"
                cnt_row = DBModel.fetch_one(m_sql, (r['id'],))
                if cnt_row:
                    managed_count = cnt_row['cnt']
            
            result.append({
                'id': r['id'],
                'username': r['username'],
                'role': r['role'],
                'customer_id': r['customer_id'],
                'is_active': r['is_active'],
                'created_at': r['created_at'],
                'linked_customer_name': r['linked_customer_name'],
                'managed_customers_count': managed_count
            })
        return result

    @staticmethod
    def get_by_username(username):
        return UserModel.query.filter_by(username=username).first()

    @staticmethod
    def create(username, password, role, customer_id=None):
        hashed_pw = generate_password_hash(password, method='scrypt')
        new_user = UserModel(username=username, password=hashed_pw, role=role, customer_id=customer_id)
        db.session.add(new_user)
        db.session.commit()
        return new_user.id

    @staticmethod
    def update(user_id, username=None, role=None, password=None, customer_id=None):
        user = UserModel.query.get(user_id)
        if not user: return False
        
        if username: user.username = username
        if role: user.role = role
        if password: user.password = generate_password_hash(password, method='scrypt')
        if customer_id is not None: user.customer_id = customer_id if customer_id else None
        
        db.session.commit()
        return True

    @staticmethod
    def toggle_active(user_id):
        user = UserModel.query.get(user_id)
        if user:
            user.is_active = not user.is_active
            db.session.commit()
            return True
        return False

    @staticmethod
    def delete(user_id):
        user = UserModel.query.get(user_id)
        if user:
            db.session.delete(user)
            db.session.commit()
            return True
        return False

    @staticmethod
    def create_client(username, password, full_name, email=None, phone=None):
        from .customer import CustomerModel
        # 1. Tạo customer
        new_customer = CustomerModel(name=full_name, email=email, phone=phone)
        db.session.add(new_customer)
        db.session.flush() # Lấy ID
        
        # 2. Tạo user
        hashed_pw = generate_password_hash(password, method='scrypt')
        new_user = UserModel(username=username, password=hashed_pw, role='client', customer_id=new_customer.id)
        db.session.add(new_user)
        db.session.commit()
        
        return new_user.id
