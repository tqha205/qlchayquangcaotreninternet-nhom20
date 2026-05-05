import random
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Lấy instance logger
logger = logging.getLogger(__name__)

# Tham chiếu tới DBModel
def get_db():
    from app.models.base import DBModel
    return DBModel

def job_auto_sync_mock_data():
    """
    Kịch bản tạo Mock Data: 
    Tự động sinh dữ liệu chi tiêu hàng ngày (daily_spending) cho các chiến dịch 'Đang chạy'.
    Cập nhật lại tổng 'spent' của chiến dịch đó.
    """
    logger.info("[JOB] Bắt đầu đồng bộ Mock Data...")
    try:
        DBModel = get_db()
        # 1. Lấy danh sách chiến dịch đang chạy
        campaigns = DBModel.fetch_all("SELECT id, budget, spent FROM campaigns WHERE status = 'Đang chạy' AND is_deleted = 0")
        
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        for c in campaigns:
            cam_id = c['id']
            budget = float(c['budget'] or 0)
            spent  = float(c['spent'] or 0)
            
            # Nếu đã tiêu hết tiền, bỏ qua (Budget Alert Job sẽ xử lý)
            if spent >= budget:
                continue
                
            # Random chi tiêu 1 ngày: từ 100k -> 500k (nhưng không vượt quá budget còn lại)
            daily_spent = random.randint(100000, 500000)
            remaining   = budget - spent
            if daily_spent > remaining:
                daily_spent = remaining
                
            # Random clicks, impressions
            impressions = random.randint(1000, 10000)
            clicks      = int(impressions * random.uniform(0.01, 0.05)) # CTR 1-5%
            
            # Thêm vào daily_spending (NẾU hôm nay chưa có)
            # Kiểm tra xem hôm nay có chưa
            exist = DBModel.fetch_one("SELECT id FROM daily_spending WHERE campaign_id = %s AND date = %s", (cam_id, today_str))
            if not exist:
                DBModel.execute(
                    "INSERT INTO daily_spending (campaign_id, date, amount_spent, clicks, impressions) VALUES (%s, %s, %s, %s, %s)",
                    (cam_id, today_str, daily_spent, clicks, impressions)
                )
                # Cập nhật tổng spent
                DBModel.execute("UPDATE campaigns SET spent = spent + %s WHERE id = %s", (daily_spent, cam_id))
                logger.info(f"  + Chiến dịch #{cam_id}: +{daily_spent}đ")
                
        logger.info("[JOB] Đồng bộ Mock Data hoàn tất.")
    except Exception as e:
        logger.error(f"[JOB ERROR] job_auto_sync_mock_data: {str(e)}")

def job_budget_alert():
    """
    Kịch bản tự động cảnh báo cạn ngân sách:
    - Nếu spent >= budget * 0.9 -> Gửi Notification (budget_warning)
    - Nếu spent >= budget -> Gửi Notification (budget_exceeded) VÀ update status = 'Kết thúc'
    """
    logger.info("[JOB] Bắt đầu quét ngân sách...")
    try:
        from app.models.notification import NotificationModel
        DBModel = get_db()
        
        # 1. Lấy các chiến dịch cần xử lý (với JOIN để lấy thông tin marketer_id, customer_id)
        sql = """
            SELECT c.id, c.name, c.budget, c.spent, c.status, c.customer_id, cu.marketer_id 
            FROM campaigns c
            LEFT JOIN customers cu ON c.customer_id = cu.id
            WHERE c.status = 'Đang chạy' AND c.is_deleted = 0 AND c.budget > 0
        """
        campaigns = DBModel.fetch_all(sql)
        
        for c in campaigns:
            cam_id = c['id']
            name   = c['name']
            budget = float(c['budget'] or 0)
            spent  = float(c['spent'] or 0)
            ratio  = spent / budget if budget > 0 else 0
            
            # Lấy list user_ids cần gửi thông báo (client, marketer)
            targets = []
            
            # Tìm account client liên kết với customer_id
            if c['customer_id']:
                client_usr = DBModel.fetch_one("SELECT id FROM users WHERE customer_id = %s", (c['customer_id'],))
                if client_usr: targets.append(client_usr['id'])
            
            # Thêm marketer_id
            if c['marketer_id']:
                targets.append(c['marketer_id'])
                
            # Loại bỏ duplicate
            targets = list(set(targets))
            
            if ratio >= 1.0:
                # Đã vượt/bằng ngân sách -> Dừng chiến dịch
                DBModel.execute("UPDATE campaigns SET status = 'Kết thúc', approval_status = 'ended' WHERE id = %s", (cam_id,))
                msg = f"Chiến dịch '{name}' đã đạt 100% ngân sách và tự động kết thúc."
                for uid in targets:
                    NotificationModel.create(uid, NotificationModel.TYPE_BUDGET_EXCEEDED, msg, title="Ngân sách cạn kiệt")
                logger.info(f"  > Kết thúc chiến dịch #{cam_id}")
                
            elif ratio >= 0.9:
                # Cảnh báo 90%
                msg = f"Chiến dịch '{name}' đã chi tiêu {(ratio*100):.1f}% ngân sách. Vui lòng nạp thêm tiền để không bị gián đoạn."
                for uid in targets:
                    # Kiểm tra xem hôm nay đã gửi cảnh báo warning cho chiến dịch này chưa để tránh gửi lặp lại
                    # (Ở đây ta tạm gửi liên tục mỗi khi job chạy, trong thực tế cần 1 bảng tracking)
                    NotificationModel.create(uid, NotificationModel.TYPE_BUDGET_WARNING, msg, title="Cảnh báo ngân sách")
                logger.info(f"  > Cảnh báo ngân sách chiến dịch #{cam_id}")
                
        logger.info("[JOB] Quét ngân sách hoàn tất.")
    except Exception as e:
        logger.error(f"[JOB ERROR] job_budget_alert: {str(e)}")

def _trigger_celery_sync():
    """Trigger Celery task nếu worker đang chạy, fallback sang hàm trực tiếp."""
    try:
        from app.tasks import sync_mock_data
        sync_mock_data.delay()
        logger.info("[SCHEDULER] Đã gửi sync_mock_data → Celery queue.")
    except Exception:
        logger.warning("[SCHEDULER] Celery không khả dụng, chạy trực tiếp (fallback).")
        job_auto_sync_mock_data()


def _trigger_celery_budget_alert():
    """Trigger Celery task nếu worker đang chạy, fallback sang hàm trực tiếp."""
    try:
        from app.tasks import budget_alert
        budget_alert.delay()
        logger.info("[SCHEDULER] Đã gửi budget_alert → Celery queue.")
    except Exception:
        logger.warning("[SCHEDULER] Celery không khả dụng, chạy trực tiếp (fallback).")
        job_budget_alert()


def init_scheduler(app):
    """
    Khởi tạo APScheduler và đăng ký các Jobs.
    APScheduler đóng vai trò trigger, logic nặng được đẩy vào Celery worker.
    Fallback sang chạy trực tiếp nếu Celery/Redis chưa được cài đặt.
    Chỉ chạy khi không phải ở chế độ reloader (để tránh chạy 2 lần).
    """
    import os
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        return  # Chỉ chạy trong tiến trình chính

    scheduler = BackgroundScheduler()

    # Chạy mỗi 1 phút → kích hoạt Celery task sync_mock_data
    scheduler.add_job(
        func=_trigger_celery_sync,
        trigger=IntervalTrigger(minutes=1),
        id='auto_sync_mock_data',
        name='Sinh dữ liệu giả lập chi tiêu (→ Celery)',
        replace_existing=True
    )

    # Chạy mỗi 1 phút 30 giây → kích hoạt Celery task budget_alert
    scheduler.add_job(
        func=_trigger_celery_budget_alert,
        trigger=IntervalTrigger(minutes=1, seconds=30),
        id='budget_alert',
        name='Cảnh báo cạn ngân sách (→ Celery)',
        replace_existing=True
    )

    scheduler.start()
    logger.info("[SCHEDULER] Hệ thống Tự động hóa đã khởi chạy (chế độ Celery-aware).")
