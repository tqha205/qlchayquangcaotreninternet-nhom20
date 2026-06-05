import requests
from app.models.base import DBModel

user = DBModel.fetch_one("SELECT * FROM users WHERE username = 'tusena'")
cust_id = user['customer_id']

# Get from live server
try:
    res = requests.get(f'http://127.0.0.1:5001/admin/api/client/metrics?cust_id={cust_id}')
    print("LIVE STATUS:", res.status_code)
    print("LIVE DATA:", res.text)
except Exception as e:
    print("Error:", e)
