from .base import DBModel

class CampaignModel(DBModel):

    @staticmethod
    def get_by_role(role, customer_id=None, marketer_id=None):
        """Lấy danh sách chiến dịch theo quyền. Client chỉ thấy của mình, Marketer thấy của khách họ quản lý."""
        query = """
            SELECT c.*, cust.name AS customer_name
            FROM campaigns c
            LEFT JOIN customers cust ON c.customer_id = cust.id
            WHERE c.is_deleted = 0
        """
        params = []
        if role == 'client' and customer_id:
            query += " AND c.customer_id = %s"
            params.append(customer_id)
        elif role == 'marketer' and marketer_id:
            query += " AND cust.marketer_id = %s"
            params.append(marketer_id)
            
        query += " ORDER BY c.created_at DESC"
        return DBModel.fetch_all(query, tuple(params) if params else None)

    @staticmethod
    def get_by_customer(customer_id):
        """Lấy danh sách chiến dịch của 1 khách hàng cụ thể."""
        query = """
            SELECT c.*, cust.name AS customer_name
            FROM campaigns c
            LEFT JOIN customers cust ON c.customer_id = cust.id
            WHERE c.customer_id = %s AND c.is_deleted = 0
            ORDER BY c.created_at DESC
        """
        return DBModel.fetch_all(query, (customer_id,))

    @staticmethod
    def get_by_id(campaign_id):
        """Lấy một chiến dịch theo ID."""
        return DBModel.fetch_one(
            "SELECT c.*, cust.name AS customer_name FROM campaigns c "
            "LEFT JOIN customers cust ON c.customer_id = cust.id "
            "WHERE c.id = %s AND c.is_deleted = 0",
            (campaign_id,)
        )

    @staticmethod
    def create(name, customer_id, platform, budget, start_date=None, end_date=None, target_link=None, objective=None, platform_id=None, approval_status='pending'):
        """Tạo chiến dịch mới. Trả về ID vừa tạo."""
        from datetime import datetime
        if not start_date: start_date = datetime.now().strftime('%Y-%m-%d')
        
        query = """
            INSERT INTO campaigns (name, objective, customer_id, platform, platform_id, target_link, budget, spent, status, approval_status, start_date, end_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 0, 'Chờ duyệt', %s, %s, %s)
        """
        return DBModel.execute(query, (name, objective, customer_id, platform, platform_id, target_link, budget, approval_status, start_date, end_date))

    @staticmethod
    def update(campaign_id, name, platform, target_link, budget, spent, status, start_date, end_date, approval_status=None, platform_id=None):
        """Cập nhật thông tin chiến dịch."""
        query = """
            UPDATE campaigns
            SET name=%s, platform=%s, target_link=%s, budget=%s, spent=%s, status=%s,
                start_date=%s, end_date=%s
        """
        params = [name, platform, target_link, budget, spent, status, start_date, end_date]
        
        if approval_status:
            query += ", approval_status=%s"
            params.append(approval_status)
        if platform_id is not None:
            query += ", platform_id=%s"
            params.append(platform_id)
            
        query += " WHERE id=%s AND is_deleted = 0"
        params.append(campaign_id)
        
        return DBModel.execute(query, tuple(params))

    @staticmethod
    def delete(campaign_id):
        """Xóa chiến dịch (Soft Delete)."""
        return DBModel.execute("UPDATE campaigns SET is_deleted = 1 WHERE id = %s", (campaign_id,))

    @staticmethod
    def get_efficiency_stats(campaign_id):
        """
        Tính chỉ số hiệu quả chiến dịch dựa trên spent/budget.
        Dữ liệu clicks/impressions được giả lập từ chi phí.
        """
        cam = CampaignModel.get_by_id(campaign_id)
        if not cam:
            return None

        budget = float(cam['budget'] or 0)
        spent  = float(cam['spent']  or 0)

        # Tỷ lệ đã tiêu
        spent_ratio = (spent / budget) if budget > 0 else 0

        # Giả lập: mỗi 1.000đ chi → 10 impressions, 0.5 clicks
        impressions = spent * 10
        clicks      = spent * 0.5

        ctr = (clicks / impressions * 100) if impressions > 0 else 0   # %
        cpc = (spent / clicks)             if clicks > 0      else 0   # đ/click

        # Xác định label hiệu quả
        if spent_ratio < 0.8:
            label     = 'Tốt'
            label_css = 'bg-emerald-50 text-emerald-700'
        elif spent_ratio < 0.9:
            label     = 'Cần tối ưu'
            label_css = 'bg-amber-50 text-amber-700'
        else:
            label     = 'Cảnh báo'
            label_css = 'bg-red-50 text-red-700'

        return {
            'spent_ratio': round(spent_ratio * 100, 1),
            'impressions': int(impressions),
            'clicks':      int(clicks),
            'ctr':         round(ctr, 2),
            'cpc':         round(cpc),
            'label':       label,
            'label_css':   label_css,
        }
    @staticmethod
    def update_status(campaign_id, status):
        """Cập nhật trạng thái chiến dịch."""
        return DBModel.execute("UPDATE campaigns SET status = %s WHERE id = %s", (status, campaign_id))

    @staticmethod
    def update_spent(campaign_id, total_spent):
        """Đồng bộ tổng chi tiêu."""
        return DBModel.execute("UPDATE campaigns SET spent = %s WHERE id = %s", (total_spent, campaign_id))
