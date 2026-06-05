from app import create_app
from app.models.base import DBModel
from app.models.daily_report import DailyReportModel
from datetime import datetime, timedelta

app = create_app()

with app.app_context():
    # Tìm user tusena
    user = DBModel.fetch_one("SELECT * FROM users WHERE username = 'tusena'")
    if not user or not user.get('customer_id'):
        print("Không tìm thấy user tusena hoặc chưa liên kết khách hàng.")
    else:
        cust_id = user['customer_id']
        # Tìm một chiến dịch của khách hàng này
        cam = DBModel.fetch_one("SELECT * FROM campaigns WHERE customer_id = %s LIMIT 1", (cust_id,))
        if not cam:
            # Nếu chưa có chiến dịch, tạo một cái
            DBModel.execute("INSERT INTO campaigns (name, customer_id, platform, budget, status) VALUES ('Chiến dịch Mùa Hè', %s, 'Facebook', 5000000, 'Đang chạy')", (cust_id,))
            cam = DBModel.fetch_one("SELECT * FROM campaigns WHERE customer_id = %s ORDER BY id DESC LIMIT 1", (cust_id,))
        
        # Thêm dữ liệu cho ngày hôm qua (để tính delta)
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        DailyReportModel.log_daily(cam['id'], yesterday, 150000, 200, 4500, 12)
        
        # Thêm dữ liệu cho ngày hôm nay
        today = datetime.now().strftime('%Y-%m-%d')
        DailyReportModel.log_daily(cam['id'], today, 250000, 350, 6000, 25)
        
        # Cập nhật số dư nếu bằng 0
        DBModel.execute("UPDATE customers SET balance = 5000000 WHERE id = %s AND (balance IS NULL OR balance = 0)", (cust_id,))
        
        print("Success")
