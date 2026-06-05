from app import create_app
from app.models.campaign import CampaignModel

app = create_app()
with app.app_context():
    try:
        campaigns = CampaignModel.get_by_customer(3)
        print("Campaigns:", campaigns)
        for c in campaigns:
            print("ID:", c.id, "Name:", c.name)
            eff = CampaignModel.get_efficiency_stats(c.id)
            print("Efficiency:", eff)
    except Exception as e:
        print("Error:", repr(e))
