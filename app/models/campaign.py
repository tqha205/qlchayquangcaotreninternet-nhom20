from app.extensions import db
from datetime import datetime

class CampaignModel(db.Model):
    __tablename__ = 'campaigns'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    objective = db.Column(db.String(255))
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    platform = db.Column(db.String(50))
    platform_id = db.Column(db.String(100))
    target_link = db.Column(db.String(512))
    budget = db.Column(db.Numeric(18, 2), default=0.00)
    spent = db.Column(db.Numeric(18, 2), default=0.00)
    status = db.Column(db.String(50), default='Chờ duyệt') # Mới thêm theo yêu cầu Prompt 1
    approval_status = db.Column(db.String(50), default='pending')
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def get_by_role(role, customer_id=None, marketer_id=None):
        query = CampaignModel.query.join(CampaignModel.customer).filter(CampaignModel.is_deleted == False)
        if role == 'client' and customer_id:
            query = query.filter(CampaignModel.customer_id == customer_id)
        elif role == 'marketer' and marketer_id:
            from .customer import CustomerModel
            query = query.filter(CustomerModel.marketer_id == marketer_id)
        
        return query.order_by(CampaignModel.created_at.desc()).all()

    @staticmethod
    def get_by_customer(customer_id):
        return CampaignModel.query.filter_by(customer_id=customer_id, is_deleted=False).order_by(CampaignModel.created_at.desc()).all()

    @staticmethod
    def get_by_id(campaign_id):
        return CampaignModel.query.filter_by(id=campaign_id, is_deleted=False).first()

    @staticmethod
    def create(name, customer_id, platform, budget, start_date=None, end_date=None, target_link=None, objective=None, platform_id=None, approval_status='pending'):
        new_campaign = CampaignModel(
            name=name, customer_id=customer_id, platform=platform, budget=budget,
            start_date=start_date, end_date=end_date, target_link=target_link,
            objective=objective, platform_id=platform_id, approval_status=approval_status
        )
        db.session.add(new_campaign)
        db.session.commit()
        return new_campaign.id

    @staticmethod
    def update(campaign_id, name, platform, target_link, budget, spent, status, start_date, end_date, approval_status=None, platform_id=None):
        campaign = CampaignModel.query.get(campaign_id)
        if campaign:
            campaign.name = name
            campaign.platform = platform
            campaign.target_link = target_link
            campaign.budget = budget
            campaign.spent = spent
            campaign.status = status
            campaign.start_date = start_date
            campaign.end_date = end_date
            if approval_status: campaign.approval_status = approval_status
            if platform_id is not None: campaign.platform_id = platform_id
            db.session.commit()
            return True
        return False

    @staticmethod
    def delete(campaign_id):
        campaign = CampaignModel.query.get(campaign_id)
        if campaign:
            campaign.is_deleted = True
            db.session.commit()
            return True
        return False

    @staticmethod
    def get_efficiency_stats(campaign_id):
        cam = CampaignModel.get_by_id(campaign_id)
        if not cam: return None

        if cam.status == 'Chờ duyệt' or cam.approval_status == 'pending':
            return {
                'spent_ratio': 0, 'impressions': 0, 'clicks': 0, 'ctr': 0, 'cpc': 0,
                'label': 'Chờ duyệt', 'label_css': 'bg-slate-100 text-slate-600',
            }

        budget = float(cam.budget or 0)
        spent = float(cam.spent or 0)
        spent_ratio = (spent / budget) if budget > 0 else 0
        impressions = spent * 10
        clicks = spent * 0.5
        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        cpc = (spent / clicks) if clicks > 0 else 0

        if spent_ratio < 0.8:
            label, label_css = 'Tốt', 'bg-emerald-50 text-emerald-700'
        elif spent_ratio < 0.9:
            label, label_css = 'Cần tối ưu', 'bg-amber-50 text-amber-700'
        else:
            label, label_css = 'Cảnh báo', 'bg-red-50 text-red-700'

        return {
            'spent_ratio': round(spent_ratio * 100, 1),
            'impressions': int(impressions),
            'clicks': int(clicks),
            'ctr': round(ctr, 2),
            'cpc': round(cpc),
            'label': label,
            'label_css': label_css,
        }

    @staticmethod
    def update_status(campaign_id, status):
        campaign = CampaignModel.query.get(campaign_id)
        if campaign:
            campaign.status = status
            db.session.commit()
            return True
        return False

    @staticmethod
    def update_spent(campaign_id, total_spent):
        campaign = CampaignModel.query.get(campaign_id)
        if campaign:
            campaign.spent = total_spent
            db.session.commit()
            return True
        return False
