from app import create_app
from app.models.base import DBModel

app = create_app()

with app.test_client() as client:
    with client.session_transaction() as sess:
        sess['role'] = 'client'
        user = DBModel.fetch_one("SELECT * FROM users WHERE username = 'tusena'")
        sess['customer_id'] = user['customer_id']
        sess['user_id'] = user['id']
        
    resp = client.get('/admin/api/client/metrics')
    print("STATUS:", resp.status_code)
    print("DATA:", resp.get_data(as_text=True))
