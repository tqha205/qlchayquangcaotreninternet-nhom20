from app import create_app
from flask import session
from app.controllers.admin_controller import get_customer_campaigns
import json

app = create_app()

with app.test_request_context('/admin/api/customers/3/campaigns'):
    session['role'] = 'admin'
    session['user_id'] = 1
    
    response = get_customer_campaigns(3)
    if hasattr(response, 'get_data'):
        # Decode the utf-8 payload
        data = json.loads(response.get_data(as_text=True))
        with open('test_output.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("Success! Output written to test_output.json")
    else:
        print("Response:", response)
