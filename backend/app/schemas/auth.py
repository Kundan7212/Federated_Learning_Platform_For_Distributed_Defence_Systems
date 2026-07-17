from pydantic import BaseModel, field_validator

# Using str instead of EmailStr so that internal addresses like
# xyz.local (which use a non-public TLD) are accepted.
# Pydantic v2 EmailStr rejects .local domains via DNS validation.

class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v

    @field_validator("username")
    @classmethod
    def username_length(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError("Username must be at least 2 characters")
        return v.strip()

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user_id: str
    username: str
    email: str

class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    is_active: bool
    is_admin: bool
    model_config = {"from_attributes": True}
