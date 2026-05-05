from pydantic import BaseModel, Field, EmailStr

class LoginSchema(BaseModel):
    username: str = Field(..., min_length=3, message="Tên đăng nhập không hợp lệ")
    password: str = Field(..., min_length=6, message="Mật khẩu quá ngắn")

class RegisterSchema(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr | None = None
    phone: str | None = None
