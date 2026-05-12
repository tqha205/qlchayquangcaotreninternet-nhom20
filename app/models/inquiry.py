from app.extensions import db
from datetime import datetime

class InquiryModel(db.Model):
    __tablename__ = 'inquiries'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    service = db.Column(db.String(100))
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default='NEW') # NEW, READ, REPLIED
    admin_note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def create(data):
        new_inquiry = InquiryModel(
            name=data['name'],
            email=data['email'],
            phone=data['phone'],
            service=data['service'],
            message=data['message']
        )
        db.session.add(new_inquiry)
        db.session.commit()
        return new_inquiry.id

    @staticmethod
    def get_all():
        return InquiryModel.query.order_by(InquiryModel.created_at.desc()).all()

    @staticmethod
    def get_by_status(status):
        return InquiryModel.query.filter_by(status=status).order_by(InquiryModel.created_at.desc()).all()

    @staticmethod
    def mark_read(inquiry_id):
        inquiry = InquiryModel.query.get(inquiry_id)
        if inquiry and inquiry.status == 'NEW':
            inquiry.status = 'READ'
            db.session.commit()
            return True
        return False

    @staticmethod
    def approve(inquiry_id):
        from .customer import CustomerModel
        inquiry = InquiryModel.query.get(inquiry_id)
        if not inquiry:
            return None

        try:
            # 1. Tạo customer mới từ dữ liệu inquiry
            new_customer = CustomerModel(
                name=inquiry.name,
                email=inquiry.email,
                phone=inquiry.phone
            )
            db.session.add(new_customer)
            
            # 2. Cập nhật trạng thái inquiry
            inquiry.status = 'REPLIED'
            
            db.session.commit()
            return new_customer.id

        except Exception as e:
            db.session.rollback()
            raise e

