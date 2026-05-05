from .base import DBModel

class PlatformModel(DBModel):
    """Model quản lý nền tảng quảng cáo (Facebook, Google...)."""

    @staticmethod
    def get_all():
        sql = "SELECT * FROM platforms ORDER BY name ASC"
        return DBModel.fetch_all(sql)

    @staticmethod
    def get_by_id(platform_id):
        sql = "SELECT * FROM platforms WHERE id = %s"
        return DBModel.fetch_one(sql, (platform_id,))

    @staticmethod
    def create(name, account_id=None, status='active'):
        sql = "INSERT INTO platforms (name, account_id, status) VALUES (%s, %s, %s)"
        return DBModel.execute(sql, (name, account_id, status))

    @staticmethod
    def update(platform_id, name, account_id, status):
        sql = "UPDATE platforms SET name=%s, account_id=%s, status=%s WHERE id=%s"
        return DBModel.execute(sql, (name, account_id, status, platform_id))

    @staticmethod
    def delete(platform_id):
        sql = "DELETE FROM platforms WHERE id = %s"
        return DBModel.execute(sql, (platform_id,))
