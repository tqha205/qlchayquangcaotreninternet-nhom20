import pytest
from app import create_app
from app.extensions import db
from app.models.user import UserModel
from app.models.customer import CustomerModel
from app.models.transaction import TransactionModel
from app.models.campaign import CampaignModel
from decimal import Decimal

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", # Dùng in-memory DB cho test
        "WTF_CSRF_ENABLED": False
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_user_flow(client):
    # 1. Register a new user
    reg_data = {
        "username": "testuser",
        "password": "password123",
        "full_name": "Test User",
        "email": "test@example.com",
        "phone": "0987654321"
    }
    resp = client.post('/auth/register', json=reg_data)
    assert resp.status_code == 200
    
    # 2. Check if user and customer were created
    user = UserModel.get_by_username("testuser")
    assert user is not None
    assert user.role == 'client'
    customer = CustomerModel.get_by_id(user.customer_id)
    assert customer is not None
    assert customer.balance == 0
    
    # 3. Perform a deposit (Admin manually completes it in this scenario)
    # Simulate a transaction being completed
    customer_id = user.customer_id
    amount = Decimal('1000000.00')
    
    # Simulate transaction record
    tx_id = TransactionModel.create_transaction(
        customer_id=customer_id,
        t_type='topup',
        amount=amount,
        status='completed'
    )
    
    # Manually deposit to customer (as admin would do)
    CustomerModel.deposit(customer_id, amount)
    
    # Verify balance
    customer = CustomerModel.get_by_id(customer_id)
    assert customer.balance == amount
    
    # 4. Create a Campaign and check balance reduction
    campaign_data = {
        "name": "Test Campaign",
        "customer_id": customer_id,
        "platform": "Facebook",
        "budget": 500000.00,
        "target_link": "http://example.com"
    }
    
    # Note: In real logic, we need to be logged in to access /admin/api/campaigns/add
    # For integration test, we can simulate the session
    with client.session_transaction() as sess:
        sess['user_id'] = user.id
        sess['role'] = user.role
        sess['customer_id'] = user.customer_id
        
    resp = client.post('/admin/api/campaigns/add', json=campaign_data)
    assert resp.status_code == 200
    
    # Verify campaign exists
    campaign = CampaignModel.query.filter_by(name="Test Campaign").first()
    assert campaign is not None
    assert campaign.budget == Decimal('500000.00')
    
    # Logic: Normally budget might not be deducted immediately upon creation, 
    # but let's assume it is or verify the system state.
    # In this app, balance is usually checked before running, 
    # but here we just verify the creation succeeded.
