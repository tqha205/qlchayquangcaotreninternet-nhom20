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
from datetime import datetime
from celery_worker import celery

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
        from app.models.base import DBModel
        campaigns = DBModel.fetch_all(
            "SELECT id, budget, spent FROM campaigns WHERE status = 'Đang chạy' AND is_deleted = 0"
        )
        today_str = datetime.now().strftime('%Y-%m-%d')

        for c in campaigns:
            cam_id = c['id']
            budget = float(c['budget'] or 0)
            spent  = float(c['spent'] or 0)
            if spent >= budget:
                continue

            daily_spent = random.randint(100000, 500000)
            remaining   = budget - spent
            if daily_spent > remaining:
                daily_spent = remaining

            impressions = random.randint(1000, 10000)
            clicks      = int(impressions * random.uniform(0.01, 0.05))

            exist = DBModel.fetch_one(
                "SELECT id FROM daily_spending WHERE campaign_id = %s AND date = %s",
                (cam_id, today_str)
            )
            if not exist:
                DBModel.execute(
                    "INSERT INTO daily_spending (campaign_id, date, amount_spent, clicks, impressions) VALUES (%s, %s, %s, %s, %s)",
                    (cam_id, today_str, daily_spent, clicks, impressions)
                )
                DBModel.execute(
                    "UPDATE campaigns SET spent = spent + %s WHERE id = %s",
                    (daily_spent, cam_id)
                )
                logger.info(f"  + Chiến dịch #{cam_id}: +{daily_spent}đ")

        logger.info("[CELERY TASK] Đồng bộ Mock Data hoàn tất.")
        return {"status": "ok", "campaigns_processed": len(campaigns)}

    except Exception as exc:
        logger.error(f"[CELERY ERROR] sync_mock_data: {str(exc)}")
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
        from app.models.notification import NotificationModel
        from app.models.base import DBModel

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

            targets = []
            if c['customer_id']:
                client_usr = DBModel.fetch_one(
                    "SELECT id FROM users WHERE customer_id = %s", (c['customer_id'],)
                )
                if client_usr:
                    targets.append(client_usr['id'])
            if c['marketer_id']:
                targets.append(c['marketer_id'])
            targets = list(set(targets))

            if ratio >= 1.0:
                DBModel.execute(
                    "UPDATE campaigns SET status = 'Kết thúc', approval_status = 'ended' WHERE id = %s",
                    (cam_id,)
                )
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

    except Exception as exc:
        logger.error(f"[CELERY ERROR] budget_alert: {str(exc)}")
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
    import requests
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
    except Exception as exc:
        logger.error(f"[CELERY ERROR] send_telegram: {str(exc)}")
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
