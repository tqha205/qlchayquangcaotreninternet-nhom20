from app.extensions import db
from datetime import datetime

class InvoiceModel(db.Model):
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True) # Đổi thành True để hỗ trợ hóa đơn chưa thanh toán
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=True) # Liên kết với Campaign
    invoice_number = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    status = db.Column(db.String(50), default='unpaid') # 'unpaid', 'pending_approval', 'paid'
    file_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    transaction = db.relationship('TransactionModel', backref=db.backref('invoice', uselist=False))
    customer = db.relationship('CustomerModel', backref=db.backref('invoices', lazy=True))
    campaign = db.relationship('CampaignModel', backref=db.backref('invoices', lazy=True))

    @staticmethod
    def create_invoice(transaction_id, customer_id, invoice_number, amount, file_path):
        invoice = InvoiceModel(
            transaction_id=transaction_id,
            customer_id=customer_id,
            invoice_number=invoice_number,
            amount=amount,
            file_path=file_path,
            status='paid'
        )
        db.session.add(invoice)
        db.session.commit()
        return invoice

    @staticmethod
    def create_for_campaign(campaign):
        """Tự động sinh ra hóa đơn chưa thanh toán khi chiến dịch được phê duyệt."""
        invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{campaign.id:04d}"
        
        # Tránh tạo trùng lặp hóa đơn cho một chiến dịch
        existing = InvoiceModel.query.filter_by(campaign_id=campaign.id).first()
        if existing:
            return existing

        invoice = InvoiceModel(
            campaign_id=campaign.id,
            customer_id=campaign.customer_id,
            invoice_number=invoice_number,
            amount=campaign.budget,
            status='unpaid'
        )
        db.session.add(invoice)
        db.session.commit()
        return invoice

