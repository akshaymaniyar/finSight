from pydantic import BaseModel
from typing import Optional


class AuthUrlResponse(BaseModel):
    authorization_url: str


class UserResponse(BaseModel):
    id: int
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    token: str
    user: UserResponse
