from app.extensions import db
from datetime import datetime

class TransactionModel(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    type = db.Column(db.String(50)) # 'deposit', 'withdraw', 'refund'
    amount = db.Column(db.Numeric(18, 2), default=0.00)
    description = db.Column(db.String(500))
    payment_method = db.Column(db.String(100))
    proof_image = db.Column(db.String(255))
    status = db.Column(db.String(50), default='pending') # 'pending', 'completed', 'rejected'
    reject_reason = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    customer = db.relationship('CustomerModel', backref=db.backref('transactions', lazy=True))

    @staticmethod
    def get_by_customer(customer_id):
        return TransactionModel.query.filter_by(customer_id=customer_id).order_by(TransactionModel.created_at.desc()).all()

    @staticmethod
    def create_transaction(customer_id, t_type, amount, description='', payment_method=None, proof_image=None, status='pending'):
        new_transaction = TransactionModel(
            customer_id=customer_id, type=t_type, amount=amount,
            description=description, payment_method=payment_method,
            proof_image=proof_image, status=status
        )
        db.session.add(new_transaction)
        db.session.commit()
        return new_transaction.id

    @staticmethod
    def get_all(customer_id=None, status=None):
        query = TransactionModel.query
        if customer_id:
            query = query.filter_by(customer_id=customer_id)
        if status:
            query = query.filter_by(status=status)
        
        return query.order_by(TransactionModel.created_at.desc()).all()

    @staticmethod
    def get_by_id(transaction_id):
        return TransactionModel.query.get(transaction_id)

    @staticmethod
    def update_status(transaction_id, status, reject_reason=None):
        transaction = TransactionModel.query.get(transaction_id)
        if transaction:
            transaction.status = status
            transaction.reject_reason = reject_reason
            db.session.commit()
            return True
        return False

    @staticmethod
    def get_invoices(customer_id):
        # Giả sử bảng invoices chưa được chuyển sang SQLAlchemy, 
        # nhưng ở đây chúng ta nên chuẩn hóa nó nếu cần.
        # Tạm thời để trống hoặc giả lập.
        return []
