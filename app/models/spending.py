from app.extensions import db
from datetime import datetime

class SpendingModel(db.Model):
    __tablename__ = 'daily_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False)
    report_date = db.Column(db.Date, nullable=False)
    daily_spent = db.Column(db.Numeric(18, 2), default=0.00)
    clicks = db.Column(db.Integer, default=0)
    impressions = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    campaign = db.relationship('CampaignModel', backref=db.backref('daily_reports', lazy=True))

    @staticmethod
    def log_daily_spending(campaign_id, date, amount_spent, clicks=0, impressions=0):
        # Sử dụng logic update nếu đã tồn tại record cho ngày đó
        existing = SpendingModel.query.filter_by(campaign_id=campaign_id, report_date=date).first()
        if existing:
            existing.daily_spent += db.type_coerce(amount_spent, db.Numeric(18, 2))
            existing.clicks += clicks
            existing.impressions += impressions
        else:
            new_report = SpendingModel(
                campaign_id=campaign_id, report_date=date, 
                daily_spent=amount_spent, clicks=clicks, impressions=impressions
            )
            db.session.add(new_report)
        db.session.commit()
        return True

    @staticmethod
    def get_spending_trend(campaign_id, limit=30):
        reports = SpendingModel.query.filter_by(campaign_id=campaign_id)\
            .order_by(SpendingModel.report_date.desc()).limit(limit).all()
        return [
            {
                'date': r.report_date,
                'amount_spent': float(r.daily_spent),
                'clicks': r.clicks,
                'impressions': r.impressions
            } for r in reports
        ]

    @staticmethod
    def get_total_spent(campaign_id):
        from sqlalchemy import func
        total = db.session.query(func.sum(SpendingModel.daily_spent))\
            .filter(SpendingModel.campaign_id == campaign_id).scalar()
        return float(total) if total else 0.0

    @staticmethod
    def get_recent_logs(limit=10, marketer_id=None):
        query = SpendingModel.query.join(SpendingModel.campaign)
        if marketer_id:
            from .customer import CustomerModel
            query = query.join(CustomerModel).filter(CustomerModel.marketer_id == marketer_id)
        
        reports = query.order_by(SpendingModel.id.desc()).limit(limit).all()
        return [
            {
                'id': r.id,
                'campaign_id': r.campaign_id,
                'report_date': r.report_date,
                'daily_spent': float(r.daily_spent),
                'clicks': r.clicks,
                'impressions': r.impressions,
                'campaign_name': r.campaign.name,
                'platform': r.campaign.platform
            } for r in reports
        ]
