from app.extensions import db
from datetime import datetime
from .base import DBModel

class CustomerModel(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    company = db.Column(db.String(255))
    status = db.Column(db.String(50), default='Tiềm năng')
    balance = db.Column(db.Numeric(18, 2), default=0.00)
    marketer_id = db.Column(db.Integer, db.ForeignKey('users.id', use_alter=True, name='fk_customer_marketer'), nullable=True)
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    marketer = db.relationship('UserModel', backref=db.backref('managed_customers', lazy=True), foreign_keys=[marketer_id])
    campaigns = db.relationship('CampaignModel', backref='customer', lazy=True)

    # Dictionary compatibility layer (both bracket and .get() access)
    def __getitem__(self, item):
        return getattr(self, item)

    def get(self, key, default=None):
        return getattr(self, key, default)

    @staticmethod
    def get_all(marketer_id=None):
        """Lấy toàn bộ khách hàng kèm số chiến dịch (subquery)."""
        query = """
            SELECT
                c.id, c.name, c.email, c.phone, c.company, c.status, c.created_at, c.marketer_id,
                u.username AS marketer_name,
                (SELECT COUNT(*) FROM campaigns cam WHERE cam.customer_id = c.id AND cam.is_deleted = 0) AS total_campaigns,
                (SELECT COUNT(*) FROM campaigns cam
                    WHERE cam.customer_id = c.id AND cam.status = 'Đang chạy' AND cam.is_deleted = 0) AS active_campaigns,
                (SELECT COALESCE(SUM(cam.budget), 0)
                    FROM campaigns cam WHERE cam.customer_id = c.id AND cam.is_deleted = 0) AS total_budget
            FROM customers c
            LEFT JOIN users u ON c.marketer_id = u.id
            WHERE c.is_deleted = 0
        """
        params = []
        if marketer_id:
            query += " AND c.marketer_id = %s"
            params.append(marketer_id)
        
        query += " ORDER BY c.id DESC"
        
        rows = DBModel.fetch_all(query, params)
        for r in rows:
            r['total_budget'] = float(r.get('total_budget') or 0)
        return rows

    @staticmethod
    def get_by_id(customer_id):
        """Lấy thông tin một khách hàng bao gồm số dư."""
        return CustomerModel.query.filter_by(id=customer_id, is_deleted=False).first()

    @staticmethod
    def deposit(customer_id, amount):
        """Cộng tiền vào tài khoản khách hàng sử dụng Pessimistic Locking (SELECT ... FOR UPDATE)."""
        customer = CustomerModel.query.with_for_update().filter_by(id=customer_id, is_deleted=False).first()
        if customer:
            customer.balance = float(customer.balance or 0) + float(amount)
            db.session.commit()
            return True
        return False

    @staticmethod
    def deduct(customer_id, amount):
        """Trừ tiền tài khoản khách hàng sử dụng Pessimistic Locking (SELECT ... FOR UPDATE)."""
        customer = CustomerModel.query.with_for_update().filter_by(id=customer_id, is_deleted=False).first()
        if customer:
            current_balance = float(customer.balance or 0)
            deduct_amount = float(amount)
            if current_balance >= deduct_amount:
                customer.balance = current_balance - deduct_amount
                db.session.commit()
                return True
        return False

    @staticmethod
    def create(name, email=None, phone=None, company=None, status='Tiềm năng', marketer_id=None):
        """Thêm khách hàng mới. Trả về ID vừa tạo."""
        new_customer = CustomerModel(
            name=name, email=email, phone=phone, company=company, 
            status=status, marketer_id=marketer_id
        )
        db.session.add(new_customer)
        db.session.commit()
        return new_customer.id

    @staticmethod
    def update(customer_id, name, email=None, phone=None, company=None, status=None, marketer_id=None):
        """Cập nhật thông tin khách hàng."""
        customer = CustomerModel.query.get(customer_id)
        if customer:
            customer.name = name
            customer.email = email
            customer.phone = phone
            customer.company = company
            if status: customer.status = status
            customer.marketer_id = marketer_id
            db.session.commit()
            return True
        return False

    @staticmethod
    def delete(customer_id):
        """Xóa khách hàng (Soft Delete)."""
        customer = CustomerModel.query.get(customer_id)
        if customer:
            customer.is_deleted = True
            # Soft-delete tất cả chiến dịch liên quan
            from .campaign import CampaignModel
            CampaignModel.query.filter_by(customer_id=customer_id).update({'is_deleted': True})
            db.session.commit()
            return True
        return False
