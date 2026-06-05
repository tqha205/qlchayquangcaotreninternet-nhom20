from app import create_app
from flask import session
from app.controllers.admin_controller import get_audit_logs
import traceback

app = create_app()

try:
    with app.test_request_context('/admin/api/admin/audit-logs'):
        session['role'] = 'admin'
        session['user_id'] = 1
        
        response = get_audit_logs()
        print("Success! No crash on get_audit_logs().")
except Exception as e:
    print("Crash on get_audit_logs()!")
    traceback.print_exc()
