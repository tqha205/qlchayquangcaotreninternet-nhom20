from flask import Blueprint, request, jsonify
from app.extensions import db, csrf
from app.models.transaction import TransactionModel
from app.models.customer import CustomerModel
from app.models.audit_log import AuditLogModel
from app.models.user import UserModel
from app.utils.payment_helpers import process_completed_transaction
import re

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/webhook', methods=['POST'])
@csrf.exempt
def webhook():
    """
    Webhook endpoint nhận thông báo biến động số dư từ dịch vụ VietQR / Casso / SePay.
    Mọi yêu cầu đến endpoint này được miễn trừ CSRF.
    """
    data = request.json or {}
    
    # 1. Parse thông tin số tiền và nội dung chuyển khoản hỗ trợ cả SePay và Casso
    amount = 0.0
    description = ""
    
    # Kiểm tra cấu trúc SePay (amountIn, transactionContent) hoặc Casso gốc
    amount_in = data.get('amountIn') or data.get('amount')
    if amount_in is not None:
        amount = float(amount_in)
        description = data.get('transactionContent') or data.get('description') or ''
    
    # Kiểm tra cấu trúc Casso lồng ghép (danh sách dữ liệu)
    elif 'data' in data and isinstance(data['data'], list) and len(data['data']) > 0:
        casso_item = data['data'][0]
        amount = float(casso_item.get('amount') or 0)
        description = casso_item.get('description') or ''
        
    if amount <= 0:
        return jsonify({'success': False, 'message': 'Không tìm thấy số tiền hợp lệ.'}), 400

    # 2. Phân tích Transaction ID hoặc Mã nạp tiền từ nội dung chuyển khoản (Memo)
    # Ví dụ: "NAP 123", "HTD123", "GD 123", "INV-2024-123" hoặc chỉ "123"
    tx_id = None
    match = re.search(r'(?:NAP|HTD|GD|INV|TX)?\s*(\d+)', description, re.IGNORECASE)
    if match:
        tx_id = int(match.group(1))

    # 3. Đối soát tìm kiếm giao dịch tương ứng
    transaction = None
    if tx_id:
        transaction = TransactionModel.query.filter_by(id=tx_id, status='pending').first()
        
    # Fallback: Đối soát theo số tiền chính xác nếu không tìm thấy ID khớp
    if not transaction:
        transaction = TransactionModel.query.filter_by(amount=amount, status='pending').first()

    if not transaction:
        return jsonify({
            'success': False, 
            'message': f'Không tìm thấy giao dịch pending khớp với số tiền {amount:,.0f}đ hoặc mã trong nội dung: "{description}"'
        }), 404

    try:
        # 4. Cập nhật số dư khách hàng bằng cơ chế Pessimistic Locking (SELECT ... FOR UPDATE)
        # đã được tích hợp trực tiếp trong hàm CustomerModel.deposit()
        CustomerModel.deposit(transaction.customer_id, amount)
        
        # 5. Cập nhật trạng thái giao dịch
        TransactionModel.update_status(transaction.id, 'completed')
        
        # 6. Kích hoạt tự động tạo hóa đơn PDF bằng Reportlab & gửi email bằng Celery
        process_completed_transaction(transaction)
        
        # 7. Ghi nhận lịch sử hệ thống (Audit Log)
        user = UserModel.query.filter_by(customer_id=transaction.customer_id).first()
        system_user_id = user.id if user else 1
        
        AuditLogModel.log(
            user_id=system_user_id,
            action='WEBHOOK_AUTO_DEPOSIT',
            target_table='transactions',
            target_id=transaction.id,
            old_value='pending',
            new_value={
                'status': 'completed', 
                'amount': amount, 
                'payment_method': 'VietQR_Webhook', 
                'description': description
            }
        )
        
        return jsonify({
            'success': True,
            'message': f'Giao dịch #{transaction.id} được đối soát tự động thành công. Đã nạp {amount:,.0f}đ!'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Lỗi hệ thống: {str(e)}'}), 500
