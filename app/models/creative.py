from .base import DBModel

class CreativeModel(DBModel):

    @staticmethod
    def get_by_campaign(campaign_id):
        """Lấy tất cả mẫu quảng cáo của một chiến dịch."""
        query = "SELECT * FROM creatives WHERE campaign_id = %s ORDER BY created_at DESC"
        return DBModel.fetch_all(query, (campaign_id,))

    @staticmethod
    def get_by_id(creative_id):
        """Lấy thông tin chi tiết một mẫu quảng cáo."""
        query = "SELECT * FROM creatives WHERE id = %s"
        return DBModel.fetch_one(query, (creative_id,))

    @staticmethod
    def create(campaign_id, name, media_type, media_url, content):
        """Thêm mới một mẫu quảng cáo (Marketer/Admin)."""
        query = """
            INSERT INTO creatives (campaign_id, name, media_type, media_url, content, status)
            VALUES (%s, %s, %s, %s, %s, 'Chờ duyệt')
        """
        return DBModel.execute(query, (campaign_id, name, media_type, media_url, content))

    @staticmethod
    def update_status(creative_id, status, feedback=None):
        """Cập nhật trạng thái mẫu quảng cáo (Khách hàng duyệt/từ chối)."""
        query = "UPDATE creatives SET status = %s, feedback = %s WHERE id = %s"
        return DBModel.execute(query, (status, feedback, creative_id))

    @staticmethod
    def delete(creative_id):
        """Xóa mẫu quảng cáo."""
        query = "DELETE FROM creatives WHERE id = %s"
        return DBModel.execute(query, (creative_id,))
