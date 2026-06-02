from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    username: str
    password: str
    email: EmailStr


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: int


class RefreshRequest(BaseModel):
    refresh_token: str
