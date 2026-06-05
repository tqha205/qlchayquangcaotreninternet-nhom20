import requests

session = requests.Session()
res = session.post('http://127.0.0.1:5001/auth/login', json={'username': 'admin', 'password': '123456'})
print("Login status:", res.status_code)
if res.status_code != 200:
    print(res.text[:500])

res = session.get('http://127.0.0.1:5001/admin/campaigns/5')
print("Status:", res.status_code)
if res.status_code == 500:
    print("CRASHED!")
    print(res.text[:2000])
