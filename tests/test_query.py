from app import create_app
from app.models.base import DBModel
import json
import decimal

app = create_app()

def default(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError

with app.app_context():
    user = DBModel.fetch_one("SELECT * FROM users WHERE username = 'tusena'")
    cust_id = user['customer_id']
    
    sql_metrics = """
        SELECT SUM(daily_spent) as total_spent,
               SUM(conversions) as total_conv,
               SUM(daily_spent) / NULLIF(SUM(conversions), 0) as cpl
        FROM daily_reports dr
        JOIN campaigns c ON dr.campaign_id = c.id
        WHERE c.customer_id = %s AND c.is_deleted = 0
    """
    metrics = DBModel.fetch_one(sql_metrics, (cust_id,))
    print(json.dumps(metrics, default=default))
