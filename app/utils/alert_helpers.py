import logging
from app.models.base import DBModel
from app.models.notification import NotificationModel
from app.extensions import socketio

logger = logging.getLogger(__name__)

def check_customer_balance_and_alert(customer_id):
    """
    Tự động quét số dư của khách hàng.
    Nếu balance < 500.000đ -> Gửi thông báo trực tiếp qua socket.io
    và ghi nhận vào bảng notifications (với type = 'budget_warning').
    """
    if not customer_id:
        return
        
    try:
        # 1. Lấy balance và tên của khách hàng
        cust = DBModel.fetch_one("SELECT name, balance FROM customers WHERE id = %s", (customer_id,))
        if not cust:
            return
            
        balance = float(cust['balance'] or 0)
        
        # 2. Nếu số dư dưới 500.000 VNĐ
        if balance < 500000:
            # Tìm user_id liên kết với customer_id
            user = DBModel.fetch_one("SELECT id FROM users WHERE customer_id = %s", (customer_id,))
            if user:
                uid = user['id']
                msg = f"Tài khoản của bạn chỉ còn {balance:,.0f} VNĐ (Dưới ngưỡng an toàn 500.000 VNĐ). Vui lòng nạp thêm tiền để không làm gián đoạn chiến dịch quảng cáo."
                title = "Cảnh báo cạn số dư ví"
                
                # Tránh Spam: Chỉ tạo thông báo mới nếu trong vòng 3 giờ qua chưa có thông báo tương tự
                recent_warn = DBModel.fetch_one("""
                    SELECT id FROM notifications 
                    WHERE user_id = %s AND type = 'budget_warning' 
                      AND title = %s AND created_at > NOW() - INTERVAL 3 HOUR
                    LIMIT 1
                """, (uid, title))
                
                if not recent_warn:
                    # Ghi vào notifications database
                    NotificationModel.create(uid, 'budget_warning', msg, title=title)
                    
                    # Phát tín hiệu qua SocketIO tới room của user đó
                    socketio.emit('low_balance_warning', {
                        'title': title,
                        'message': msg,
                        'balance': balance,
                        'user_id': uid
                    }, room=f"user_{uid}")
                    
                    logger.warning(f"[LOW BALANCE ALERT] User #{uid} balance: {balance:,.0f}đ. Alert sent.")
    except Exception as e:
        logger.error(f"[check_customer_balance_and_alert Error] {str(e)}")
