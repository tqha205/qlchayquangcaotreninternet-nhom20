from .base import DBModel

class SpendingModel(DBModel):
    """Model quản lý chi tiêu quảng cáo hàng ngày."""

    @staticmethod
    def log_daily_spending(campaign_id, date, amount_spent, clicks=0, impressions=0):
        sql = """
            INSERT INTO daily_reports (campaign_id, report_date, daily_spent, clicks, impressions)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                daily_spent = daily_spent + VALUES(daily_spent),
                clicks = clicks + VALUES(clicks),
                impressions = impressions + VALUES(impressions)
        """
        return DBModel.execute(sql, (campaign_id, date, amount_spent, clicks, impressions))

    @staticmethod
    def get_spending_trend(campaign_id, limit=30):
        """Lấy xu hướng chi tiêu theo ngày của chiến dịch."""
        sql = """
            SELECT report_date as date, daily_spent as amount_spent, clicks, impressions
            FROM daily_reports
            WHERE campaign_id = %s
            ORDER BY report_date DESC
            LIMIT %s
        """
        return DBModel.fetch_all(sql, (campaign_id, limit))

    @staticmethod
    def get_total_spent(campaign_id):
        sql = "SELECT SUM(daily_spent) AS total FROM daily_reports WHERE campaign_id = %s"
        row = DBModel.fetch_one(sql, (campaign_id,))
        return float(row['total']) if row and row['total'] else 0.0
