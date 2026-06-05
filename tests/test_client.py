from app import create_app
from flask import session

app = create_app()
app.testing = True
client = app.test_client()

with client.session_transaction() as sess:
    sess['role'] = 'admin'
    sess['user_id'] = 1

print("Testing /admin/campaigns...")
res = client.get('/admin/campaigns')
print("Status:", res.status_code)
if res.status_code == 500:
    print(res.text)

print("Testing /admin/campaigns/1...")
res = client.get('/admin/campaigns/1')
print("Status:", res.status_code)
if res.status_code == 500:
    print(res.text)
