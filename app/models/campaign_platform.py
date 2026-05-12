from .base import DBModel


class CampaignPlatformModel(DBModel):
    """Model quản lý quan hệ nhiều-nhiều giữa Campaign và Platform.
    
    Mỗi chiến dịch có thể chạy trên nhiều nền tảng, mỗi nền tảng 
    có ngân sách phân bổ riêng và theo dõi chi tiêu độc lập.
    """

    @staticmethod
    def get_by_campaign(campaign_id):
        """Lấy tất cả nền tảng của một chiến dịch kèm thống kê."""
        sql = """
            SELECT 
                cp.id, cp.campaign_id, cp.platform_id, 
                cp.budget_alloc, cp.spent, cp.status, cp.created_at,
                p.name AS platform_name,
                p.account_id AS platform_account,
                p.status AS platform_conn_status,
                -- Chỉ số hiệu quả từ daily_spending
                COALESCE(SUM(ds.clicks), 0)      AS total_clicks,
                COALESCE(SUM(ds.impressions), 0) AS total_impressions,
                COALESCE(SUM(ds.amount_spent), 0) AS confirmed_spent
            FROM campaign_platforms cp
            JOIN platforms p ON cp.platform_id = p.id
            LEFT JOIN daily_spending ds ON ds.campaign_id = cp.campaign_id 
                AND ds.camp_platform_id = cp.id
            WHERE cp.campaign_id = %s
            GROUP BY cp.id
            ORDER BY cp.created_at ASC
        """
        try:
            rows = DBModel.fetch_all(sql, (campaign_id,))
        except Exception as e:
            # Nếu bảng chưa tồn tại (Migration chưa chạy), trả về rỗng thay vì lỗi 500
            if "1146" in str(e) or "doesn't exist" in str(e).lower():
                return []
            raise e

        # Tính CTR, CPC
        for r in rows:
            impressions = int(r.get('total_impressions') or 0)
            clicks      = int(r.get('total_clicks') or 0)
            spent       = float(r.get('confirmed_spent') or r.get('spent') or 0)
            r['ctr'] = round(clicks / impressions * 100, 2) if impressions > 0 else 0.0
            r['cpc'] = round(spent / clicks, 0) if clicks > 0 else 0
            r['budget_alloc'] = float(r.get('budget_alloc') or 0)
            r['spent']        = float(r.get('spent') or 0)
        return rows

    @staticmethod
    def get_by_id(cp_id):
        """Lấy một bản ghi campaign_platforms theo ID."""
        return DBModel.fetch_one(
            "SELECT cp.*, p.name AS platform_name FROM campaign_platforms cp "
            "JOIN platforms p ON cp.platform_id = p.id WHERE cp.id = %s",
            (cp_id,)
        )

    @staticmethod
    def add(campaign_id, platform_id, budget_alloc=0):
        """Thêm một nền tảng vào chiến dịch. Bỏ qua nếu đã tồn tại."""
        sql = """
            INSERT INTO campaign_platforms (campaign_id, platform_id, budget_alloc, spent)
            VALUES (%s, %s, %s, 0)
            ON DUPLICATE KEY UPDATE budget_alloc = VALUES(budget_alloc)
        """
        return DBModel.execute(sql, (campaign_id, platform_id, budget_alloc))

    @staticmethod
    def remove(campaign_id, platform_id):
        """Xóa một nền tảng khỏi chiến dịch."""
        return DBModel.execute(
            "DELETE FROM campaign_platforms WHERE campaign_id = %s AND platform_id = %s",
            (campaign_id, platform_id)
        )

    @staticmethod
    def update_budget(campaign_id, platform_id, budget_alloc):
        """Cập nhật ngân sách phân bổ cho một nền tảng."""
        return DBModel.execute(
            "UPDATE campaign_platforms SET budget_alloc = %s WHERE campaign_id = %s AND platform_id = %s",
            (budget_alloc, campaign_id, platform_id)
        )

    @staticmethod
    def update_spent(campaign_id, platform_id, spent):
        """Cập nhật chi tiêu tích lũy cho một nền tảng."""
        return DBModel.execute(
            "UPDATE campaign_platforms SET spent = %s WHERE campaign_id = %s AND platform_id = %s",
            (spent, campaign_id, platform_id)
        )

    @staticmethod
    def update_status(cp_id, status):
        """Cập nhật trạng thái hoạt động của một nền tảng trong chiến dịch."""
        return DBModel.execute(
            "UPDATE campaign_platforms SET status = %s WHERE id = %s",
            (status, cp_id)
        )

    @staticmethod
    def get_total_alloc(campaign_id):
        """Tổng ngân sách đã phân bổ cho chiến dịch."""
        row = DBModel.fetch_one(
            "SELECT COALESCE(SUM(budget_alloc), 0) as total FROM campaign_platforms WHERE campaign_id = %s",
            (campaign_id,)
        )
        return float(row['total']) if row else 0.0

    @staticmethod
    def get_daily_chart_data(campaign_id, days=30):
        """Lấy dữ liệu chi tiêu hàng ngày theo từng nền tảng (dùng cho biểu đồ)."""
        sql = """
            SELECT 
                ds.date,
                p.name AS platform_name,
                SUM(ds.amount_spent) AS daily_spent,
                SUM(ds.clicks)       AS daily_clicks,
                SUM(ds.impressions)  AS daily_impressions
            FROM daily_spending ds
            JOIN campaign_platforms cp ON ds.camp_platform_id = cp.id
            JOIN platforms p ON cp.platform_id = p.id
            WHERE ds.campaign_id = %s
              AND ds.date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            GROUP BY ds.date, p.name
            ORDER BY ds.date ASC
        """
        return DBModel.fetch_all(sql, (campaign_id, days))

    @staticmethod
    def compute_payment_status(campaign_id, customer_balance):
        """
        Tính trạng thái thanh toán dựa trên số dư khách hàng.
        
        Returns:
            'paid'        — Số dư >= tổng ngân sách phân bổ
            'pending'     — Có giao dịch nạp tiền đang chờ xác nhận
            'underfunded' — Số dư không đủ
        """
        total_alloc = CampaignPlatformModel.get_total_alloc(campaign_id)
        
        # Kiểm tra giao dịch pending của khách hàng
        pending = DBModel.fetch_one("""
            SELECT COUNT(*) as cnt 
            FROM transactions t
            JOIN campaigns c ON c.id = %s
            WHERE t.customer_id = c.customer_id AND t.status = 'pending' AND t.type = 'topup'
        """, (campaign_id,))
        
        has_pending = pending and int(pending['cnt']) > 0
        
        if customer_balance >= total_alloc:
            return 'paid'
        elif has_pending:
            return 'pending'
        else:
            return 'underfunded'
