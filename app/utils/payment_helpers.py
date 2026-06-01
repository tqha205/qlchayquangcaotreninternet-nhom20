from datetime import datetime
from app.extensions import db
from app.models.invoice import InvoiceModel
from app.utils.invoice_generator import generate_invoice_pdf
from app.models.customer import CustomerModel

def process_completed_transaction(transaction):
    """
    Xử lý sau khi giao dịch thành công:
    1. Sinh PDF hóa đơn.
    2. Lưu hóa đơn vào cơ sở dữ liệu.
    3. Gửi email đính kèm hóa đơn (Celery task).
    """
    try:
        # Lấy thông tin khách hàng
        customer = CustomerModel.query.get(transaction.customer_id)
        if not customer:
            return False
            
        invoice_date = transaction.created_at or datetime.utcnow()
        date_str = invoice_date.strftime('%Y%m%d')
        invoice_number = f"INV-{date_str}-{transaction.id:04d}"
        
        # 1. Sinh file PDF hóa đơn chuyên nghiệp bằng reportlab
        rel_path, abs_path = generate_invoice_pdf(transaction, customer)
        
        # 2. Tạo bản ghi hóa đơn trong database
        invoice = InvoiceModel.query.filter_by(transaction_id=transaction.id).first()
        if not invoice:
            InvoiceModel.create_invoice(
                transaction_id=transaction.id,
                customer_id=customer.id,
                invoice_number=invoice_number,
                amount=transaction.amount,
                file_path=rel_path
            )
            
        # 3. Kích hoạt Celery task gửi email nếu có địa chỉ email của khách hàng
        if customer.email:
            from app.tasks import send_invoice_email
            send_invoice_email.delay(
                customer_email=customer.email,
                customer_name=customer.name,
                amount=transaction.amount,
                invoice_number=invoice_number,
                pdf_path=abs_path
            )
        return True
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"[INVOICING ERROR] Thất bại khi tạo hóa đơn cho GD #{transaction.id}: {e}")
        return False
