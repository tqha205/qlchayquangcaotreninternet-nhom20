from app import create_app
from flask import session
from app.controllers.admin_controller import campaigns
import traceback

app = create_app()

try:
    with app.test_request_context('/admin/campaigns'):
        session['role'] = 'admin'
        session['user_id'] = 1
        
        response = campaigns()
        print("Success! No crash on campaigns().")
except Exception as e:
    print("Crash on campaigns()!")
    traceback.print_exc()
