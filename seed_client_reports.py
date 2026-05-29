from app import create_app
from app.models.base import DBModel
from datetime import date, timedelta
import random

app = create_app()
with app.app_context():
    print("Seeding dummy daily reports for customer 'tusena' (ID: 5)...")
    
    # Get campaigns of customer 5
    campaigns = DBModel.fetch_all("SELECT id, budget FROM campaigns WHERE is_deleted = 0 AND customer_id = 5")
    if not campaigns:
        print("No campaigns found for customer 5.")
    else:
        # Ensure customer has balance
        DBModel.execute("UPDATE customers SET balance = 5000000 WHERE id = 5")
        print("Updated customer 5 (Nguyen Huu Tu) balance to 5,000,000.")
        
        for campaign in campaigns:
            cid = campaign['id']
            # Clear old reports to avoid duplicates
            DBModel.execute("DELETE FROM daily_reports WHERE campaign_id = %s", (cid,))
            
            # Seed last 8 days (including today)
            for i in range(7, -1, -1):
                day = date.today() - timedelta(days=i)
                
                # Normal day: 100k spent, 50 clicks, 500 impressions, 2 conversions
                spent = 120000 + random.randint(-15000, 15000)
                clicks = 60 + random.randint(-10, 10)
                impressions = clicks * 15 + random.randint(-50, 50)
                conversions = random.randint(1, 4)
                
                # Make TODAY have higher spent and clicks to look fresh
                if i == 0:
                    spent = 175000
                    clicks = 85
                    impressions = 1250
                    conversions = 5
                    
                DBModel.execute("""
                    INSERT INTO daily_reports (campaign_id, report_date, daily_spent, clicks, impressions, conversions)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (cid, day, spent, clicks, impressions, conversions))
                
            print(f"Seeded 8 days of reports for campaign ID {cid}")
            
            # Update the campaign total spent
            total_spent = DBModel.fetch_one("SELECT SUM(daily_spent) as total FROM daily_reports WHERE campaign_id = %s", (cid,))['total'] or 0
            DBModel.execute("UPDATE campaigns SET spent = %s WHERE id = %s", (total_spent, cid))
            
    print("Done. All reports for customer 5 are successfully seeded!")
