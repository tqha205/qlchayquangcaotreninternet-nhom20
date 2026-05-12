from functools import wraps
from flask import request, jsonify
from pydantic import BaseModel, EmailStr, HttpUrl, Field, validator
from typing import Optional, Any

class CampaignCreateSchema(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    customer_id: int
    platform: str
    budget: float = Field(..., gt=0)
    target_link: Optional[HttpUrl] = None
    objective: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    @validator('budget')
    def budget_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Ngân sách phải là số dương')
        return v

def validate_schema(schema: Any):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                data = request.get_json()
                schema(**data)
            except Exception as e:
                return jsonify({
                    'success': False, 
                    'message': 'Dữ liệu không hợp lệ', 
                    'errors': str(e)
                }), 400
            return f(*args, **kwargs)
        return decorated_function
    return decorator
