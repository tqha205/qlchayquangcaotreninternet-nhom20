from app import create_app
from app.models import DBModel

app = create_app()
with app.app_context():
    print("AUDIT LOGS:")
    logs = DBModel.fetch_all('SELECT id, created_at FROM audit_logs')
    for row in logs:
        print(row)
