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
    def get_total_metrics(campaign_id):
        """Lấy tổng các chỉ số của chiến dịch."""
        sql = """
            SELECT COALESCE(SUM(clicks), 0) as total_clicks,
                   COALESCE(SUM(impressions), 0) as total_impressions,
                   COALESCE(SUM(conversions), 0) as total_conversions
            FROM daily_reports
            WHERE campaign_id = %s
        """
        row = DBModel.fetch_one(sql, (campaign_id,))
        if not row:
            return {'total_clicks': 0, 'total_impressions': 0, 'total_conversions': 0}
        return row

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
    @staticmethod
    def get_cpc_cpa_fluctuations(threshold=0.2):
        """
        Tìm các chiến dịch có biến động CPC hoặc CPA bất thường (>20% so với trung bình 7 ngày).
        """
        sql = """
            WITH stats_7d AS (
                SELECT 
                    campaign_id,
                    SUM(daily_spent) / NULLIF(SUM(clicks), 0) as avg_cpc_7d,
                    SUM(daily_spent) / NULLIF(SUM(conversions), 0) as avg_cpa_7d
                FROM daily_reports
                WHERE report_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                  AND report_date < CURDATE()
                GROUP BY campaign_id
            ),
            stats_today AS (
                SELECT 
                    campaign_id,
                    daily_spent / NULLIF(clicks, 0) as cpc_today,
                    daily_spent / NULLIF(conversions, 0) as cpa_today
                FROM daily_reports
                WHERE report_date = CURDATE()
            )
            SELECT 
                c.id, c.name,
                s7.avg_cpc_7d, st.cpc_today,
                s7.avg_cpa_7d, st.cpa_today
            FROM stats_today st
            JOIN stats_7d s7 ON st.campaign_id = s7.campaign_id
            JOIN campaigns c ON st.campaign_id = c.id
            WHERE 
                ABS(st.cpc_today - s7.avg_cpc_7d) / NULLIF(s7.avg_cpc_7d, 0) > %s
                OR ABS(st.cpa_today - s7.avg_cpa_7d) / NULLIF(s7.avg_cpa_7d, 0) > %s
            LIMIT 5
        """
        rows = DBModel.fetch_all(sql, (threshold, threshold))
        for r in rows:
            r['avg_cpc_7d'] = float(r['avg_cpc_7d'] or 0)
            r['cpc_today']  = float(r['cpc_today']  or 0)
            r['avg_cpa_7d'] = float(r['avg_cpa_7d'] or 0)
            r['cpa_today']  = float(r['cpa_today']  or 0)
        return rows

    @staticmethod
    def get_total_managed_budget():
        """Tính tổng ngân sách đang quản lý và tỷ lệ chi tiêu thực tế."""
        sql = """
            SELECT 
                COALESCE(SUM(budget), 0) as total_budget,
                COALESCE(SUM(spent), 0) as total_spent
            FROM campaigns
            WHERE is_deleted = 0
        """
        return DBModel.fetch_one(sql)

    @staticmethod
    def get_cashflow_forecast():
        """
        Dự báo ngày khách hàng sẽ hết tiền dựa trên Burn Rate hiện tại (trung bình 3 ngày gần nhất).
        Chỉ tính cho các khách hàng có số dư > 0.
        """
        sql = """
            SELECT 
                cust.id, cust.name, cust.balance,
                COALESCE(SUM(dr.daily_spent), 0) / 3 as burn_rate_daily
            FROM customers cust
            LEFT JOIN campaigns c ON c.customer_id = cust.id
            LEFT JOIN daily_reports dr ON dr.campaign_id = c.id 
                 AND dr.report_date >= DATE_SUB(CURDATE(), INTERVAL 3 DAY)
            WHERE cust.balance > 0
            GROUP BY cust.id
            HAVING (COALESCE(SUM(dr.daily_spent), 0) / 3) > 0
            ORDER BY (cust.balance / (COALESCE(SUM(dr.daily_spent), 0) / 3)) ASC
            LIMIT 10
        """
        rows = DBModel.fetch_all(sql)
        for r in rows:
            r['days_remaining'] = round(float(r['balance']) / float(r['burn_rate_daily']), 1)
            r['burn_rate_daily'] = float(r['burn_rate_daily'])
            r['balance'] = float(r['balance'])
        return rows
