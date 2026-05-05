from app.models.base import DBModel
from datetime import date


class DailyReportModel(DBModel):
    """Model quản lý báo cáo chi phí hàng ngày theo chiến dịch."""

    @staticmethod
    def log_daily(campaign_id, report_date, daily_spent, clicks=0, impressions=0, conversions=0):
        """
        Ghi nhận (hoặc cộng dồn) chi phí trong ngày.
        Dùng INSERT ... ON DUPLICATE KEY UPDATE để xử lý trùng lặp.
        """
        sql = """
            INSERT INTO daily_reports
                (campaign_id, report_date, daily_spent, clicks, impressions, conversions)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                daily_spent  = daily_spent  + VALUES(daily_spent),
                clicks       = clicks       + VALUES(clicks),
                impressions  = impressions  + VALUES(impressions),
                conversions  = conversions  + VALUES(conversions)
        """
        DBModel.execute(sql, (campaign_id, report_date, daily_spent, clicks, impressions, conversions))

    @staticmethod
    def get_last_7_days(campaign_id):
        """Lấy dữ liệu 7 ngày gần nhất của một chiến dịch."""
        sql = """
            SELECT report_date, daily_spent, clicks, impressions, conversions
            FROM   daily_reports
            WHERE  campaign_id = %s
            ORDER BY report_date DESC
            LIMIT 7
        """
        rows = DBModel.fetch_all(sql, (campaign_id,))
        # Chuyển Decimal / date sang kiểu native Python để JSON safely
        result = []
        for r in rows:
            result.append({
                'report_date': r['report_date'].strftime('%Y-%m-%d') if hasattr(r['report_date'], 'strftime') else str(r['report_date']),
                'daily_spent': float(r['daily_spent'] or 0),
                'clicks':      int(r['clicks'] or 0),
                'impressions': int(r['impressions'] or 0),
                'conversions': int(r['conversions'] or 0),
            })
        return result

    @staticmethod
    def get_spending_trend_7days():
        """
        Tổng chi phí theo ngày trong 7 ngày gần nhất (toàn hệ thống).
        Trả về { labels: [...], data: [...] } dùng cho ApexCharts.
        """
        sql = """
            SELECT dr.report_date, SUM(dr.daily_spent) AS total_spent
            FROM   daily_reports dr
            WHERE  dr.report_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
            GROUP BY dr.report_date
            ORDER BY dr.report_date ASC
        """
        rows = DBModel.fetch_all(sql)
        labels = [r['report_date'].strftime('%d/%m') if hasattr(r['report_date'], 'strftime') else str(r['report_date']) for r in rows]
        data   = [float(r['total_spent'] or 0) for r in rows]
        return {'labels': labels, 'data': data}

    @staticmethod
    def get_platform_summary():
        """
        Tổng chi phí (daily_spent) nhóm theo nền tảng.
        JOIN với campaigns để lấy platform.
        """
        sql = """
            SELECT c.platform, SUM(dr.daily_spent) AS total_spent
            FROM   daily_reports dr
            JOIN   campaigns c ON dr.campaign_id = c.id
            GROUP BY c.platform
            ORDER BY total_spent DESC
        """
        rows = DBModel.fetch_all(sql)
        labels = [r['platform'] for r in rows]
        data   = [float(r['total_spent'] or 0) for r in rows]
        return {'labels': labels, 'data': data}
