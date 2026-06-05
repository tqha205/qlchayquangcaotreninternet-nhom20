from app import create_app
from flask import session
from app.controllers.admin_controller import get_campaign_creatives
import traceback

app = create_app()

with app.test_request_context('/'):
    try:
        with app.test_request_context(f'/admin/api/campaigns/1/creatives', method='GET'):
            session['role'] = 'admin'
            session['user_id'] = 1
            response = get_campaign_creatives(1)
            print("Success! No crash on creatives.")
    except Exception as e:
        print(f"Crash on creatives!")
        traceback.print_exc()
