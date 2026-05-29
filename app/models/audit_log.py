from app.models.base import DBModel
import json

class AuditLogModel(DBModel):
    """Model quản lý nhật ký hoạt động hệ thống."""

    @staticmethod
    def log(user_id, action, target_table=None, target_id=None, old_value=None, new_value=None):
        """Ghi nhận một hoạt động vào nhật ký."""
        # Chuyển đổi giá trị thành JSON hợp lệ (DB yêu cầu json_valid)
        def _to_json(val):
            if val is None:
                return None
            if isinstance(val, (dict, list)):
                return json.dumps(val, ensure_ascii=False, default=str)
            if isinstance(val, str):
                # Wrap string thành JSON string hợp lệ
                return json.dumps(val, ensure_ascii=False)
            # ORM object → chuyển sang dict các cột
            if hasattr(val, '__table__'):
                d = {c.name: getattr(val, c.name, None) for c in val.__table__.columns}
                return json.dumps(d, ensure_ascii=False, default=str)
            # Fallback: wrap thành JSON
            return json.dumps(str(val), ensure_ascii=False)
        
        old_value = _to_json(old_value)
        new_value = _to_json(new_value)

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
