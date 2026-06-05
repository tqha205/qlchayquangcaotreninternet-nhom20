from app import create_app
from app.models.base import DBModel
from app.models.daily_report import DailyReportModel
from app.models.campaign import CampaignModel
from app.models.customer import CustomerModel
from datetime import datetime, timedelta
import random

app = create_app()

with app.app_context():
    # 1. Thêm dữ liệu dự báo dòng tiền
    # Tìm một khách hàng
    cust = DBModel.fetch_one("SELECT * FROM customers WHERE balance > 0 LIMIT 1")
    if not cust:
        # Tạo khách hàng mới có balance
        DBModel.execute("INSERT INTO customers (name, email, phone, balance, status) VALUES ('Khách hàng Demo', 'demo@test.com', '0123456789', 15000000, 'active')")
        cust = DBModel.fetch_one("SELECT * FROM customers ORDER BY id DESC LIMIT 1")
    
    # Tìm chiến dịch của KH
    cam = DBModel.fetch_one("SELECT * FROM campaigns WHERE customer_id = %s LIMIT 1", (cust['id'],))
    if not cam:
        DBModel.execute("INSERT INTO campaigns (name, customer_id, platform, budget, status) VALUES ('Campaign Demo Cashflow', %s, 'Facebook', 5000000, 'Đang chạy')", (cust['id'],))
        cam = DBModel.fetch_one("SELECT * FROM campaigns ORDER BY id DESC LIMIT 1")

    # Thêm report 3 ngày gần nhất để tạo burn_rate
    for i in range(3):
        d = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        DailyReportModel.log_daily(cam['id'], d, 500000, 100, 2000, 5)

    # 2. Thêm dữ liệu biến động CPC/CPA
    # Tìm/Tạo một chiến dịch khác để tạo biến động
    DBModel.execute("INSERT INTO campaigns (name, customer_id, platform, budget, status) VALUES ('Campaign Fluctuation', %s, 'Google', 10000000, 'Đang chạy')", (cust['id'],))
    cam_fluc = DBModel.fetch_one("SELECT * FROM campaigns ORDER BY id DESC LIMIT 1")

    # 7 ngày trước: CPC trung bình thấp (1000đ/click)
    for i in range(1, 8):
        d = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        DailyReportModel.log_daily(cam_fluc['id'], d, 100000, 100, 3000, 10) # CPC = 1000

    # Hôm nay: CPC cao bất thường (2000đ/click) -> Biến động +100%
    d_today = datetime.now().strftime('%Y-%m-%d')
    DailyReportModel.log_daily(cam_fluc['id'], d_today, 200000, 100, 3000, 10) # CPC = 2000
    
    print("Đã thêm dữ liệu mẫu vào DB thành công!")
