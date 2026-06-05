from app import create_app
from flask import session
from app.controllers.admin_controller import get_campaigns
import json
import traceback

app = create_app()

try:
    with app.test_request_context('/admin/api/campaigns'):
        session['role'] = 'admin'
        session['user_id'] = 1
        
        response = get_campaigns()
        print("Success! No crash on get_campaigns().")
except Exception as e:
    print("Crash on get_campaigns()!")
    traceback.print_exc()
