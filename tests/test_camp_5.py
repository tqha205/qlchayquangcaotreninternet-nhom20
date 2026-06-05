from app import create_app
from flask import session
import traceback

app = create_app()

with app.test_request_context('/admin/campaigns/5'):
    try:
        from app.controllers.admin_controller import campaign_detail
        session['role'] = 'admin'
        session['user_id'] = 1
        res = campaign_detail(5)
        print("Success for campaign 5!")
    except Exception as e:
        print(f"Error on campaign 5: {e}")
        traceback.print_exc()
