from app import create_app
from flask import session
from app.controllers.admin_controller import campaign_detail
from app.models import DBModel
import traceback

app = create_app()

with app.test_request_context('/'):
    cams = DBModel.fetch_all("SELECT id FROM campaigns")
    print("Found", len(cams), "campaigns")
    for c in cams:
        try:
            with app.test_request_context(f'/admin/campaigns/{c["id"]}'):
                session['role'] = 'admin'
                session['user_id'] = 1
                response = campaign_detail(c['id'])
                print(f"Success! No crash on campaign {c['id']}")
        except Exception as e:
            print(f"Crash on campaign {c['id']}!")
            traceback.print_exc()
