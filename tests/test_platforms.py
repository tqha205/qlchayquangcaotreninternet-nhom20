from app import create_app
from flask import session
from app.controllers.admin_controller import get_campaign_platforms
import traceback

app = create_app()

with app.test_request_context('/'):
    try:
        with app.test_request_context(f'/admin/api/campaigns/1/platforms', method='GET'):
            session['role'] = 'admin'
            session['user_id'] = 1
            response = get_campaign_platforms(1)
            print("Success! No crash on platforms.")
    except Exception as e:
        print(f"Crash on platforms!")
        traceback.print_exc()
