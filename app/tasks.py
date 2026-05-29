"""
app/tasks.py
============
Định nghĩa các Celery Background Tasks.
Thay thế cho các hàm trong jobs.py chạy đồng bộ.

Cách kích hoạt:
    task.delay()               # Gửi vào queue ngay lập tức
    task.apply_async(countdown=60) # Trì hoãn 60 giây

Cách chạy worker:
    celery -A celery_worker.celery worker --loglevel=info
"""

import random
import logging
import mysql.connector
import requests
import requests.exceptions
from datetime import datetime
from celery import shared_task
from celery import Task
import sentry_sdk
from celery_worker import celery

# Cấu hình logging riêng cho Celery
celery_logger = logging.getLogger('celery_worker')
celery_logger.setLevel(logging.ERROR)
handler = logging.FileHandler('logs/celery_error.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
celery_logger.addHandler(handler)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# TASK 1: Đồng bộ Mock Data Chi tiêu
# ─────────────────────────────────────────────
@celery.task(name='tasks.sync_mock_data', bind=True, max_retries=3)
def sync_mock_data(self):
    """
    Task Celery: Tự động sinh dữ liệu chi tiêu hàng ngày cho các
    chiến dịch 'Đang chạy'. Thay thế cho job_auto_sync_mock_data() trong APScheduler.
    """
    logger.info("[CELERY TASK] Bắt đầu đồng bộ Mock Data...")
    try:
        from app.models.campaign import CampaignModel
        from app.extensions import db
        from sqlalchemy import text

        # Query using SQLAlchemy ORM
        campaigns = CampaignModel.query.filter(
            CampaignModel.status == 'Đang chạy',
            CampaignModel.is_deleted == False
        ).all()
        
        today_str = datetime.now().strftime('%Y-%m-%d')

        for c in campaigns:
            cam_id = c.id
            budget = float(c.budget or 0)
            spent  = float(c.spent or 0)
            if spent >= budget:
                continue

            daily_spent = random.randint(100000, 500000)
            remaining   = budget - spent
            if daily_spent > remaining:
                daily_spent = remaining

            impressions = random.randint(1000, 10000)
            clicks      = int(impressions * random.uniform(0.01, 0.05))

            # DB Transaction block for safety
            try:
                db.session.begin(nested=True)
                
                # Check if exists in daily_spending
                res = db.session.execute(
                    text("SELECT id FROM daily_spending WHERE campaign_id = :cid AND date = :date"),
                    {'cid': cam_id, 'date': today_str}
                ).fetchone()
                
                if not res:
                    db.session.execute(
                        text("INSERT INTO daily_spending (campaign_id, date, amount_spent, clicks, impressions) VALUES (:cid, :date, :spent, :clicks, :impr)"),
                        {'cid': cam_id, 'date': today_str, 'spent': daily_spent, 'clicks': clicks, 'impr': impressions}
                    )
                    c.spent = CampaignModel.spent + daily_spent
                    logger.info(f"  + Chiến dịch #{cam_id}: +{daily_spent}đ")
                
                db.session.commit()
            except mysql.connector.Error as db_err:
                db.session.rollback()
                logger.error(f"[DB TRANSACTION ERROR] Failed updating campaign {cam_id}: {db_err}")
                raise db_err
            except Exception as e:
                db.session.rollback()
                logger.error(f"[UNEXPECTED TRANSACTION ERROR] Failed updating campaign {cam_id}: {e}")
                raise e

        logger.info("[CELERY TASK] Đồng bộ Mock Data hoàn tất.")
        return {"status": "ok", "campaigns_processed": len(campaigns)}

    except mysql.connector.Error as exc:
        celery_logger.error(f"[CELERY DB ERROR] sync_mock_data: {str(exc)}")
        sentry_sdk.capture_exception(exc)
        raise self.retry(exc=exc, countdown=30)
    except Exception as exc:
        celery_logger.error(f"[CELERY UNEXPECTED ERROR] sync_mock_data: {str(exc)}")
        sentry_sdk.capture_exception(exc)
        raise self.retry(exc=exc, countdown=30)


# ─────────────────────────────────────────────
# TASK 2: Cảnh báo Ngân sách & Gửi SocketIO Push
# ─────────────────────────────────────────────
@celery.task(name='tasks.budget_alert', bind=True, max_retries=3)
def budget_alert(self):
    """
    Task Celery: Quét ngân sách các chiến dịch, gửi Notification
    và push real-time qua SocketIO khi đạt ngưỡng 90%.
    Thay thế cho job_budget_alert() trong APScheduler.
    """
    logger.info("[CELERY TASK] Bắt đầu quét ngân sách...")
    try:
        from app.models.campaign import CampaignModel
        from app.models.customer import CustomerModel
        from app.models.user import UserModel
        from app.models.notification import NotificationModel
        from app.extensions import db

        # Query using SQLAlchemy ORM (Join instead of raw SQL)
        campaigns = db.session.query(CampaignModel).join(
            CustomerModel, CampaignModel.customer_id == CustomerModel.id, isouter=True
        ).filter(
            CampaignModel.status == 'Đang chạy',
            CampaignModel.is_deleted == False,
            CampaignModel.budget > 0
        ).all()

        for c in campaigns:
            cam_id = c.id
            name   = c.name
            budget = float(c.budget or 0)
            spent  = float(c.spent or 0)
            ratio  = spent / budget if budget > 0 else 0

            targets = []
            if c.customer_id:
                client_usr = UserModel.query.filter_by(customer_id=c.customer_id).first()
                if client_usr:
                    targets.append(client_usr.id)
            if c.customer and c.customer.marketer_id:
                targets.append(c.customer.marketer_id)
            targets = list(set(targets))

            if ratio >= 1.0:
                try:
                    db.session.begin(nested=True)
                    c.status = 'Kết thúc'
                    c.approval_status = 'ended'
                    db.session.commit()
                except mysql.connector.Error as db_err:
                    db.session.rollback()
                    logger.error(f"[DB TRANSACTION ERROR] Failed ending campaign {cam_id}: {db_err}")
                    raise db_err
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"[UNEXPECTED TRANSACTION ERROR] Failed ending campaign {cam_id}: {e}")
                    raise e
                
                msg = f"Chiến dịch '{name}' đã đạt 100% ngân sách và tự động kết thúc."
                for uid in targets:
                    NotificationModel.create(uid, NotificationModel.TYPE_BUDGET_EXCEEDED, msg, title="Ngân sách cạn kiệt")
                # Gửi push SocketIO (nếu server đang chạy cùng process - emit qua redis pubsub)
                _emit_socket_notification(targets, 'budget_exceeded', {'campaign': name, 'ratio': ratio})
                logger.info(f"  > Kết thúc chiến dịch #{cam_id}")

            elif ratio >= 0.9:
                msg = f"Chiến dịch '{name}' đã chi tiêu {(ratio*100):.1f}% ngân sách."
                for uid in targets:
                    NotificationModel.create(uid, NotificationModel.TYPE_BUDGET_WARNING, msg, title="Cảnh báo ngân sách")
                _emit_socket_notification(targets, 'budget_warning', {'campaign': name, 'ratio': ratio})
                logger.info(f"  > Cảnh báo ngân sách chiến dịch #{cam_id}")

        logger.info("[CELERY TASK] Quét ngân sách hoàn tất.")
        return {"status": "ok"}

    except mysql.connector.Error as exc:
        celery_logger.error(f"[CELERY DB ERROR] budget_alert: {str(exc)}")
        sentry_sdk.capture_exception(exc)
        raise self.retry(exc=exc, countdown=30)
    except Exception as exc:
        celery_logger.error(f"[CELERY UNEXPECTED ERROR] budget_alert: {str(exc)}")
        sentry_sdk.capture_exception(exc)
        raise self.retry(exc=exc, countdown=30)


# ─────────────────────────────────────────────
# TASK 3: Gửi Tin nhắn Telegram (Heavy IO)
# ─────────────────────────────────────────────
@celery.task(name='tasks.send_telegram', bind=True, max_retries=5)
def send_telegram(self, message: str, chat_id: str = None):
    """
    Task Celery: Gửi tin nhắn Telegram bất đồng bộ.
    Tách ra khỏi request cycle để không block giao diện người dùng.
    """
    from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

    token   = TELEGRAM_BOT_TOKEN
    chat    = chat_id or TELEGRAM_CHAT_ID

    if not token or not chat:
        logger.warning("[CELERY] Telegram chưa được cấu hình, bỏ qua task.")
        return {"status": "skipped"}

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={"chat_id": chat, "text": message, "parse_mode": "Markdown"}, timeout=10)
        resp.raise_for_status()
        logger.info(f"[CELERY] Đã gửi Telegram: {message[:50]}...")
        return {"status": "sent"}
    except requests.exceptions.RequestException as exc:
        celery_logger.error(f"[CELERY TELEGRAM REQUEST ERROR] send_telegram: {str(exc)}")
        sentry_sdk.capture_exception(exc)
        raise self.retry(exc=exc, countdown=60)
    except Exception as exc:
        celery_logger.error(f"[CELERY TELEGRAM UNEXPECTED ERROR] send_telegram: {str(exc)}")
        sentry_sdk.capture_exception(exc)
        raise self.retry(exc=exc, countdown=60)


# ─────────────────────────────────────────────
# Helper nội bộ
# ─────────────────────────────────────────────
def _emit_socket_notification(user_ids: list, event: str, data: dict):
    """
    Thử emit SocketIO event tới các user_id liên quan.
    Dùng Flask-SocketIO message queue (Redis) nếu có.
    """
    try:
        from app.extensions import socketio
        for uid in user_ids:
            socketio.emit(event, {**data, 'user_id': uid}, room=f"user_{uid}")
    except Exception as e:
        logger.debug(f"[SocketIO emit skipped]: {e}")


@shared_task
def aggregate_daily_spending():
    """
    Chạy định kỳ (00:01) để tổng hợp chi tiêu ngày hôm qua từ daily_spending
    vào bảng daily_reports để tăng tốc độ Dashboard.
    """
    from app.extensions import db
    from sqlalchemy import text
    
    # 1. Lấy dữ liệu ngày hôm qua
    sql = """
        INSERT INTO daily_reports (campaign_id, report_date, daily_spent, clicks, impressions, conversions)
        SELECT campaign_id, date, SUM(amount_spent), SUM(clicks), SUM(impressions), SUM(conversions)
        FROM daily_spending
        WHERE date = DATE_SUB(CURDATE(), INTERVAL 1 DAY)
        GROUP BY campaign_id, date
        ON DUPLICATE KEY UPDATE 
            daily_spent = VALUES(daily_spent),
            clicks = VALUES(clicks),
            impressions = VALUES(impressions),
            conversions = VALUES(conversions)
    """
    try:
        db.session.execute(text(sql))
        db.session.commit()
        print("✅ Đã tổng hợp dữ liệu chi tiêu ngày hôm qua.")
    except mysql.connector.Error as e:
        db.session.rollback()
        print(f"❌ Lỗi DB tổng hợp dữ liệu: {e}")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Lỗi không xác định tổng hợp dữ liệu: {e}")
