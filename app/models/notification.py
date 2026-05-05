from app.models.base import DBModel


class NotificationModel(DBModel):
    """Model quản lý thông báo hệ thống (cảnh báo ngân sách, chiến dịch kết thúc...)."""

    # Các loại thông báo hợp lệ
    TYPE_BUDGET_WARNING  = 'budget_warning'
    TYPE_BUDGET_EXCEEDED = 'budget_exceeded'
    TYPE_CAMPAIGN_ENDED  = 'campaign_ended'

    @staticmethod
    def create(user_id, ntype, message, title='Hệ thống'):
        """
        Tạo thông báo mới.
        :param user_id: ID người dùng nhận thông báo
        :param ntype:   Loại thông báo (budget_warning / budget_exceeded / campaign_ended / info)
        :param message: Nội dung thông báo
        :param title:   Tiêu đề thông báo
        """
        sql = "INSERT INTO notifications (user_id, type, title, message) VALUES (%s, %s, %s, %s)"
        return DBModel.execute(sql, (user_id, ntype, title, message))

    @staticmethod
    def get_unread(user_id, limit=10):
        """Lấy <limit> thông báo chưa đọc của một user, mới nhất trước."""
        sql = """
            SELECT id, user_id, title, type, message, is_read, created_at
            FROM notifications
            WHERE user_id = %s AND is_read = 0
            ORDER BY created_at DESC
            LIMIT %s
        """
        rows = DBModel.fetch_all(sql, (user_id, limit))
        result = []
        for r in rows:
            result.append({
                'id':            r['id'],
                'user_id':       r['user_id'],
                'title':         r['title'],
                'type':          r['type'],
                'message':       r['message'],
                'is_read':       bool(r['is_read']),
                'created_at':    r['created_at'].strftime('%d/%m/%Y %H:%M') if hasattr(r['created_at'], 'strftime') else str(r['created_at']),
            })
        return result

    @staticmethod
    def get_unread_count(user_id):
        """Đếm số thông báo chưa đọc của user."""
        sql = "SELECT COUNT(*) AS cnt FROM notifications WHERE user_id = %s AND is_read = 0"
        row = DBModel.fetch_one(sql, (user_id,))
        return int(row['cnt']) if row else 0

    @staticmethod
    def mark_read(notification_id, user_id=None):
        """Đánh dấu một thông báo là đã đọc."""
        if user_id:
            DBModel.execute("UPDATE notifications SET is_read = 1 WHERE id = %s AND user_id = %s", (notification_id, user_id))
        else:
            DBModel.execute("UPDATE notifications SET is_read = 1 WHERE id = %s", (notification_id,))

    @staticmethod
    def mark_all_read(user_id):
        """Đánh dấu tất cả thông báo là đã đọc của user."""
        DBModel.execute("UPDATE notifications SET is_read = 1 WHERE user_id = %s AND is_read = 0", (user_id,))
