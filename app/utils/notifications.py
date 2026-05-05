import requests
import config

def send_telegram_alert(message):
    """Gửi tin nhắn cảnh báo đến Telegram."""
    token   = config.TELEGRAM_BOT_TOKEN
    chat_id = config.TELEGRAM_CHAT_ID

    if not token or not chat_id:
        print("⚠️  Telegram chưa được cấu hình. Bỏ qua gửi thông báo.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Lỗi gửi Telegram: {e}")
        return False

def check_budget_and_notify(campaign, new_spent):
    """Kiểm tra ngưỡng ngân sách và gửi cảnh báo nếu vượt 90%."""
    budget = float(campaign.get('budget', 0))
    spent  = float(new_spent)

    if budget <= 0:
        return

    ratio = spent / budget
    if ratio >= 0.9:
        # Cảnh báo 90%
        msg = (
            f"<b>🚨 CẢNH BÁO NGÂN SÁCH (90%)</b>\n\n"
            f"👤 Khách hàng: <b>{campaign.get('customer_name', 'N/A')}</b>\n"
            f"🎯 Chiến dịch: <b>{campaign.get('name')}</b>\n"
            f"💰 Ngân sách: {format(budget, ',.0f')}đ\n"
            f"💸 Đã tiêu: {format(spent, ',.0f')}đ (<b>{round(ratio*100,1)}%</b>)\n"
            f"⚠️ Còn lại: {format(budget - spent, ',.0f')}đ\n\n"
            f"<i>Vui lòng nạp thêm tiền hoặc tối ưu chiến dịch!</i>"
        )
        send_telegram_alert(msg)
