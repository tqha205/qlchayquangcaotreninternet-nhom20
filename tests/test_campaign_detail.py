from app import create_app
from flask import session
from app.controllers.admin_controller import campaign_detail
import json
import traceback

app = create_app()

try:
    with app.test_request_context('/admin/campaigns/1'):
        session['role'] = 'admin'
        session['user_id'] = 1
        
        response = campaign_detail(1)
        print("Success! No crash on campaign 1.")
except Exception as e:
    print("Crash on campaign 1!")
    traceback.print_exc()

try:
    with app.test_request_context('/admin/campaigns/2'):
        session['role'] = 'admin'
        session['user_id'] = 1
        
        response = campaign_detail(2)
        print("Success! No crash on campaign 2.")
except Exception as e:
    print("Crash on campaign 2!")
    traceback.print_exc()
