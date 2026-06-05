from app import create_app
from flask import session
from app.controllers.admin_controller import get_client_metrics

app = create_app()

with app.test_request_context('/api/client/metrics'):
    session['role'] = 'client'
    session['customer_id'] = 2 # Let's find tusena's ID
    from app.models.base import DBModel
    user = DBModel.fetch_one("SELECT * FROM users WHERE username = 'tusena'")
    session['customer_id'] = user['customer_id']
    resp = get_client_metrics()
    print("Response JSON:")
    print(resp.get_json())
