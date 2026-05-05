from app.models.base import DBModel
import json

class AuditLogModel(DBModel):
    """Model quản lý nhật ký hoạt động hệ thống."""

    @staticmethod
    def log(user_id, action, target_table=None, target_id=None, old_value=None, new_value=None):
        """Ghi nhận một hoạt động vào nhật ký."""
        # Chuyển dict sang JSON string nếu cần
        if isinstance(old_value, (dict, list)):
            old_value = json.dumps(old_value, ensure_ascii=False)
        if isinstance(new_value, (dict, list)):
            new_value = json.dumps(new_value, ensure_ascii=False)

        sql = """
            INSERT INTO audit_logs (user_id, action, target_table, target_id, old_value, new_value)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        return DBModel.execute(sql, (user_id, action, target_table, target_id, old_value, new_value))

    @staticmethod
    def get_recent(limit=50):
        """Lấy danh sách nhật ký gần đây."""
        sql = """
            SELECT al.*, u.username 
            FROM audit_logs al
            LEFT JOIN users u ON al.user_id = u.id
            ORDER BY al.created_at DESC
            LIMIT %s
        """
        return DBModel.fetch_all(sql, (limit,))
