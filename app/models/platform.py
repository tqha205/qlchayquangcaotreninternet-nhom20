from .base import DBModel

class PlatformModel(DBModel):
    """Model quản lý nền tảng quảng cáo (Facebook, Google...)."""

    @staticmethod
    def get_all():
        sql = """
            SELECT p.*, 
                   (SELECT COUNT(*) FROM campaigns c WHERE c.platform_id = p.id AND c.status = 'Đang chạy' AND c.is_deleted = 0) AS active_campaigns_count
            FROM platforms p 
            ORDER BY p.name ASC
        """
        return DBModel.fetch_all(sql)

    @staticmethod
    def get_by_id(platform_id):
        sql = "SELECT * FROM platforms WHERE id = %s"
        return DBModel.fetch_one(sql, (platform_id,))

    @staticmethod
    def get_facebook_platform():
        """Lấy nền tảng Facebook hoạt động."""
        sql = "SELECT * FROM platforms WHERE LOWER(name) LIKE '%facebook%' LIMIT 1"
        return DBModel.fetch_one(sql)

    @staticmethod
    def create(name, account_id=None, status='active', access_token=None):
        sql = "INSERT INTO platforms (name, account_id, status, access_token) VALUES (%s, %s, %s, %s)"
        return DBModel.execute(sql, (name, account_id, status, access_token))

    @staticmethod
    def update(platform_id, name, account_id, status, access_token=None):
        sql = "UPDATE platforms SET name=%s, account_id=%s, status=%s, access_token=%s WHERE id=%s"
        return DBModel.execute(sql, (name, account_id, status, access_token, platform_id))

    @staticmethod
    def update_token(platform_id, access_token, status='active'):
        """Cập nhật Access Token của nền tảng sau khi OAuth thành công."""
        sql = "UPDATE platforms SET access_token=%s, status=%s WHERE id=%s"
        return DBModel.execute(sql, (access_token, status, platform_id))

    @staticmethod
    def delete(platform_id):
        sql = "DELETE FROM platforms WHERE id = %s"
        return DBModel.execute(sql, (platform_id,))
