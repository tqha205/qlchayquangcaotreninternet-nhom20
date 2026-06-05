from app import create_app
from app.models import DBModel

app = create_app()
with app.app_context():
    print("CAMPAIGNS:")
    for row in DBModel.fetch_all('SELECT id, created_at FROM campaigns'):
        print(row)
    print("CAMPAIGN PLATFORMS:")
    for row in DBModel.fetch_all('SELECT id, created_at FROM campaign_platforms'):
        print(row)
    print("DAILY REPORTS:")
    for row in DBModel.fetch_all('SELECT id, report_date FROM daily_reports'):
        print(row)
