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
# TASK 1: Đồng bộ dữ liệu Facebook Graph API / Mock Data
# ─────────────────────────────────────────────
@celery.task(name='tasks.sync_mock_data', bind=True, max_retries=3)
def sync_mock_data(self):
    """
    Task Celery: Đồng bộ dữ liệu chi dịch QC từ Facebook Graph API thực tế thay vì mock data.
    """
    logger.info("[CELERY TASK] Bắt đầu đồng bộ dữ liệu chiến dịch từ Facebook Graph API...")
    try:
        from app.models.campaign import CampaignModel
        from app.models.platform import PlatformModel
        from app.models.daily_report import DailyReportModel
        from app.extensions import db
        import requests
        from datetime import datetime, timedelta

        # Lấy các chiến dịch đang hoạt động và không bị xóa
        campaigns = CampaignModel.query.filter(
            CampaignModel.status == 'Đang chạy',
            CampaignModel.is_deleted == False
        ).all()
        
        yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        processed_count = 0

        for c in campaigns:
            # Lấy thông tin platform tương ứng
            if not c.platform_id:
                continue
            
            platform = PlatformModel.get_by_id(c.platform_id)
            if not platform:
                continue

            # Chỉ xử lý nếu là Facebook và có access_token + account_id
            name_lower = platform.get('name', '').lower()
            access_token = platform.get('access_token')
            account_id = platform.get('account_id')

            if 'facebook' in name_lower and access_token and account_id:
                logger.info(f"Đang đồng bộ dữ liệu Facebook API cho Chiến dịch #{c.id} (Tài khoản: {account_id})")
                try:
                    # Gọi Graph API /v19.0/{account_id}/insights
                    act_id = account_id if account_id.startswith('act_') else f"act_{account_id}"
                    url = f"https://graph.facebook.com/v19.0/{act_id}/insights"
                    
                    params = {
                        'access_token': access_token,
                        'time_range': f'{{"since":"{yesterday_str}","until":"{yesterday_str}"}}',
                        'fields': 'spend,clicks,impressions',
                        'level': 'campaign'
                    }
                    
                    resp = requests.get(url, params=params, timeout=15)
                    resp.raise_for_status()
                    data = resp.json().get('data', [])
                    
                    daily_spent = 0.0
                    clicks = 0
                    impressions = 0
                    
                    if data:
                        # Graph API trả về kết quả
                        insight = data[0]
                        daily_spent = float(insight.get('spend', 0))
                        clicks = int(insight.get('clicks', 0))
                        impressions = int(insight.get('impressions', 0))
                        logger.info(f"Facebook API trả về: spend={daily_spent}, clicks={clicks}, impressions={impressions}")
                    else:
                        logger.warning(f"Facebook Graph API không trả về dữ liệu cho ngày hôm qua ({yesterday_str})")

                    # Ghi dữ liệu vào bảng daily_reports
                    DailyReportModel.log_daily(
                        campaign_id=c.id,
                        report_date=yesterday_str,
                        daily_spent=daily_spent,
                        clicks=clicks,
                        impressions=impressions,
                        conversions=int(clicks * 0.1)
                    )
                    
                    # Cộng dồn chi tiêu thực tế vào c.spent
                    db.session.begin(nested=True)
                    c.spent = CampaignModel.spent + daily_spent
                    db.session.commit()
                    processed_count += 1

                except Exception as api_err:
                    logger.error(f"Lỗi khi gọi Facebook API cho Chiến dịch #{c.id}: {api_err}")
                    if "OAuthException" in str(api_err) or "190" in str(api_err):
                        PlatformModel.update_token(platform['id'], access_token, status='error')
            else:
                # Mock fallback
                logger.info(f"Chiến dịch #{c.id} chưa kết nối Facebook API hoặc không phải Facebook. Sử dụng mock data thay thế.")
                daily_spent = random.randint(50000, 200000)
                impressions = random.randint(500, 3000)
                clicks = int(impressions * random.uniform(0.01, 0.04))
                
                DailyReportModel.log_daily(
                    campaign_id=c.id,
                    report_date=yesterday_str,
                    daily_spent=daily_spent,
                    clicks=clicks,
                    impressions=impressions,
                    conversions=int(clicks * random.uniform(0.05, 0.15))
                )
                
                db.session.begin(nested=True)
                c.spent = CampaignModel.spent + daily_spent
                db.session.commit()
                processed_count += 1

        logger.info(f"[CELERY TASK] Đồng bộ Facebook Graph API hoàn tất. Đã xử lý {processed_count} chiến dịch.")
        return {"status": "ok", "campaigns_processed": processed_count}

    except Exception as exc:
        celery_logger.error(f"[CELERY ERROR] sync_mock_data: {str(exc)}")
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


@celery.task(name='tasks.send_invoice_email', bind=True, max_retries=3)
def send_invoice_email(self, customer_email, customer_name, amount, invoice_number, pdf_path):
    """
    Task Celery: Gửi email xác nhận nạp tiền kèm đính kèm file hóa đơn PDF bằng SMTP.
    """
    import os
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders

    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER', '')
    smtp_password = os.getenv('SMTP_PASSWORD', '')
    smtp_sender = os.getenv('SMTP_SENDER', smtp_user or 'no-reply@adsmanager.com')

    logger.info(f"[CELERY] Bắt đầu gửi email hóa đơn {invoice_number} tới {customer_email}...")

    # Nếu không có tài khoản SMTP, giả lập thành công để tránh lỗi
    if not smtp_user or not smtp_password:
        logger.warning(f"[CELERY] Chưa cấu hình SMTP_USER/SMTP_PASSWORD. Giả lập gửi email thành công.")
        return {"status": "simulated", "message": "SMTP credentials missing, email simulated successfully."}

    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_sender
        msg['To'] = customer_email
        msg['Subject'] = f"[ADS Manager] Xác nhận nạp tiền thành công - Hóa đơn {invoice_number}"

        body = f"Chào {customer_name},\n\nYêu cầu nạp tiền của bạn đã được duyệt và thực hiện thành công.\n\n- Số hóa đơn: {invoice_number}\n- Số tiền nạp: {float(amount):,.0f} VNĐ\n- Thời gian: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\nChúng tôi xin đính kèm hóa đơn PDF thanh toán chi tiết của bạn trong email này.\nCảm ơn bạn đã đồng hành và sử dụng dịch vụ của ADS Manager!\n\nTrân trọng,\nĐội ngũ ADS Manager\nhttps://adsmanager.com"
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # Đính kèm file PDF hóa đơn
        if os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f"attachment; filename={os.path.basename(pdf_path)}"
                )
                msg.attach(part)
        else:
            logger.error(f"[CELERY] Không tìm thấy file PDF hóa đơn tại: {pdf_path}")

        # Kết nối SMTP và gửi
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_sender, customer_email, msg.as_string())

        logger.info(f"[CELERY] Đã gửi email thành công tới {customer_email}")
        return {"status": "sent", "recipient": customer_email}

    except Exception as exc:
        logger.error(f"[CELERY EMAIL ERROR] Thất bại khi gửi email tới {customer_email}: {str(exc)}")
        raise self.retry(exc=exc, countdown=60)
