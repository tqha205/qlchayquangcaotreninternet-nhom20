from app.extensions import db
from datetime import datetime

class CustomerModel(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    company = db.Column(db.String(255))
    status = db.Column(db.String(50), default='Tiềm năng')
    balance = db.Column(db.Numeric(18, 2), default=0.00)
    marketer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    marketer = db.relationship('UserModel', backref=db.backref('managed_customers', lazy=True), foreign_keys=[marketer_id])
    campaigns = db.relationship('CampaignModel', backref='customer', lazy=True)

    @staticmethod
    def get_all(marketer_id=None):
        """Lấy danh sách khách hàng kèm thống kê bằng SQL thuần."""
        from .base import DBModel
        params = []
        where_clause = "WHERE c.is_deleted = 0"
        if marketer_id:
            where_clause += " AND c.marketer_id = %s"
            params.append(marketer_id)
            
        sql = f"""
            SELECT 
                c.id, c.name, c.email, c.phone, c.company, c.status, c.created_at, c.marketer_id,
                u.username AS marketer_name,
                (SELECT COUNT(*) FROM campaigns cam WHERE cam.customer_id = c.id AND cam.is_deleted = 0) AS total_campaigns,
                (SELECT COUNT(*) FROM campaigns cam WHERE cam.customer_id = c.id AND cam.status = 'Đang chạy' AND cam.is_deleted = 0) AS active_campaigns,
                (SELECT SUM(budget) FROM campaigns cam WHERE cam.customer_id = c.id AND cam.is_deleted = 0) AS total_budget
            FROM customers c
            LEFT JOIN users u ON c.marketer_id = u.id
            {where_clause}
            ORDER BY c.id DESC
        """
        rows = DBModel.fetch_all(sql, tuple(params))
        
        result = []
        for r in rows:
            result.append({
                'id': r['id'],
                'name': r['name'],
                'email': r['email'],
                'phone': r['phone'],
                'company': r['company'],
                'status': r['status'],
                'created_at': r['created_at'],
                'marketer_id': r['marketer_id'],
                'marketer_name': r['marketer_name'] or 'Hệ thống',
                'total_campaigns': r['total_campaigns'] or 0,
                'active_campaigns': r['active_campaigns'] or 0,
                'total_budget': float(r['total_budget'] or 0)
            })
        return result

    @staticmethod
    def get_by_id(customer_id):
        return CustomerModel.query.filter_by(id=customer_id, is_deleted=False).first()

    @staticmethod
    def deposit(customer_id, amount):
        customer = CustomerModel.query.get(customer_id)
        if customer:
            customer.balance += db.type_coerce(amount, db.Numeric(18, 2))
            db.session.commit()
            return True
        return False

    @staticmethod
    def create(name, email=None, phone=None, company=None, status='Tiềm năng', marketer_id=None):
        new_customer = CustomerModel(
            name=name, email=email, phone=phone, company=company, 
            status=status, marketer_id=marketer_id
        )
        db.session.add(new_customer)
        db.session.commit()
        return new_customer.id

    @staticmethod
    def update(customer_id, name, email=None, phone=None, company=None, status=None, marketer_id=None):
        customer = CustomerModel.query.get(customer_id)
        if customer:
            customer.name = name
            customer.email = email
            customer.phone = phone
            customer.company = company
            customer.status = status
            customer.marketer_id = marketer_id
            db.session.commit()
            return True
        return False

    @staticmethod
    def delete(customer_id):
        customer = CustomerModel.query.get(customer_id)
        if customer:
            customer.is_deleted = True
            db.session.commit()
            return True
        return False
